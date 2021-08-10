"""The frame ignoring system for varname

There 4 mechanisms to ignore intermediate frames to determine the desired one
so that a variable name should be retrieved at that frame.

1. Ignore frames by a given module. Any calls inside it and inside its
   submodules will be ignored. A filename (path) to a module is also acceptable
   and recommended when code is executed by `exec` without module available.
2. Ignore frames by a given pair of module and a qualified name (qualname).
   See 1) for acceptable modules. The qualname should be unique in that module.
3. Ignore frames by a (non-decorated) function.
4. Ignore frames by a decorated function. In this case, you can specified a
   tuple with the function and the number of decorators of it. The decorators
   on the wrapper function inside the decorators should also be counted.

Any frames in `varname`, standard libraries, and frames of any expressions like
<lambda> are ignored by default.

"""
import sys
import inspect
from distutils import sysconfig
import warnings
from os import path
from pathlib import Path
from fnmatch import fnmatch
from abc import ABC, abstractmethod
from typing import List, Union
from types import FrameType, ModuleType, FunctionType

from executing import Source

from .utils import (
    IgnoreElemType,
    IgnoreType,
    MaybeDecoratedFunctionWarning,
    cached_getmodule,
    attach_ignore_id_to_module,
    frame_matches_module_by_ignore_id,
    check_qualname_by_source,
    debug_ignore_frame,
)


class IgnoreElem(ABC):
    """An element of the ignore list"""

    def __init_subclass__(cls, attrs: List[str]) -> None:
        """Define different attributes for subclasses"""

        def subclass_init(
            self,
            # IgnoreModule: ModuleType
            # IgnoreFilename/IgnoreDirname: str
            # IgnoreFunction: FunctionType
            # IgnoreDecorated: FunctionType, int
            # IgnoreModuleQualname/IgnoreFilenameQualname:
            #   ModuleType/str, str
            # IgnoreOnlyQualname: None, str
            *ign_args: Union[str, int, ModuleType, FunctionType],
        ) -> None:
            """__init__ function for subclasses"""
            for attr, arg in zip(attrs, ign_args):
                setattr(self, attr, arg)

            self._post_init()

        # save it for __repr__
        cls.attrs = attrs
        cls.__init__ = subclass_init  # type: ignore

    def _post_init(self) -> None:
        """Setups after __init__"""

    @abstractmethod
    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        """Whether the frame matches the ignore element"""

    def __repr__(self) -> str:
        """Representation of the element"""
        attr_values = (getattr(self, attr) for attr in self.__class__.attrs)
        # get __name__ if possible
        attr_values = (
            repr(getattr(attr_value, "__name__", attr_value))
            for attr_value in attr_values
        )
        attr_values = ", ".join(attr_values)
        return f"{self.__class__.__name__}({attr_values})"


class IgnoreModule(IgnoreElem, attrs=["module"]):
    """Ignore calls from a module or its submodules"""

    def _post_init(self) -> None:
        attach_ignore_id_to_module(self.module)

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        frame = frameinfos[frame_no].frame
        module = cached_getmodule(frame.f_code)
        if module:
            return (
                module.__name__ == self.module.__name__
                or module.__name__.startswith(f"{self.module.__name__}.")
            )

        return frame_matches_module_by_ignore_id(frame, self.module)


class IgnoreFilename(IgnoreElem, attrs=["filename"]):
    """Ignore calls from a module by matching its filename"""

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        frame = frameinfos[frame_no].frame

        # in case of symbolic links
        return path.realpath(frame.f_code.co_filename) == path.realpath(
            self.filename
        )


class IgnoreDirname(IgnoreElem, attrs=["dirname"]):
    """Ignore calls from modules inside a directory

    Currently used internally to ignore calls from standard libraries."""

    def _post_init(self) -> None:
        # pylint: disable=access-member-before-definition
        # pylint: disable=attribute-defined-outside-init

        # Path object will turn into str here
        self.dirname = path.realpath(self.dirname)  # type: str

        if not self.dirname.endswith(path.sep):
            self.dirname = f"{self.dirname}{path.sep}"

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        frame = frameinfos[frame_no].frame
        filename = path.realpath(frame.f_code.co_filename)

        return filename.startswith(self.dirname)


class IgnoreStdlib(IgnoreDirname, attrs=["dirname"]):
    """Ignore standard libraries in sysconfig.get_python_lib(standard_lib=True)

    But we need to ignore 3rd-party packages under site-packages/.
    """

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        frame = frameinfos[frame_no].frame
        third_party_lib = f"{self.dirname}site-packages{path.sep}"
        filename = path.realpath(frame.f_code.co_filename)

        return (
            filename.startswith(self.dirname)
            and
            # Exclude 3rd-party libraries in site-packages
            not filename.startswith(third_party_lib)
        )


class IgnoreFunction(IgnoreElem, attrs=["func"]):
    """Ignore a non-decorated function"""

    def _post_init(self) -> None:
        if (
            # without functools.wraps
            "<locals>" in self.func.__qualname__
            or self.func.__name__ != self.func.__code__.co_name
        ):
            warnings.warn(
                f"You asked varname to ignore function {self.func.__name__!r}, "
                "which may be decorated. If it is not intended, you may need "
                "to ignore all intermediate frames with a tuple of "
                "the function and the number of its decorators.",
                MaybeDecoratedFunctionWarning,
            )

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        frame = frameinfos[frame_no].frame
        return frame.f_code == self.func.__code__


class IgnoreDecorated(IgnoreElem, attrs=["func", "n_decor"]):
    """Ignore a decorated function"""

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        try:
            frame = frameinfos[frame_no + self.n_decor].frame
        except IndexError:
            return False

        return frame.f_code == self.func.__code__


class IgnoreModuleQualname(IgnoreElem, attrs=["module", "qualname"]):
    """Ignore calls by qualified name in the module"""

    def _post_init(self) -> None:

        attach_ignore_id_to_module(self.module)
        # check uniqueness of qualname
        modfile = getattr(self.module, "__file__", None)
        if modfile is not None:
            check_qualname_by_source(
                Source.for_filename(modfile, self.module.__dict__),
                self.module.__name__,
                self.qualname,
            )

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        frame = frameinfos[frame_no].frame
        module = cached_getmodule(frame.f_code)

        # Return earlier to avoid qualname uniqueness check
        if module and module != self.module:
            return False

        if not module and not frame_matches_module_by_ignore_id(
            frame, self.module
        ):
            return False

        source = Source.for_frame(frame)
        check_qualname_by_source(source, self.module.__name__, self.qualname)

        return fnmatch(source.code_qualname(frame.f_code), self.qualname)


class IgnoreFilenameQualname(IgnoreElem, attrs=["filename", "qualname"]):
    """Ignore calls with given qualname in the module with the filename"""

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        frame = frameinfos[frame_no].frame

        frame_filename = path.realpath(frame.f_code.co_filename)
        preset_filename = path.realpath(self.filename)
        # return earlier to avoid qualname uniqueness check
        if frame_filename != preset_filename:
            return False

        source = Source.for_frame(frame)
        check_qualname_by_source(source, self.filename, self.qualname)

        return fnmatch(source.code_qualname(frame.f_code), self.qualname)


class IgnoreOnlyQualname(IgnoreElem, attrs=["_none", "qualname"]):
    """Ignore calls that match the given qualname, across all frames."""

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        frame = frameinfos[frame_no].frame

        # module is None, check qualname only
        return fnmatch(
            Source.for_frame(frame).code_qualname(frame.f_code), self.qualname
        )


def create_ignore_elem(ignore_elem: IgnoreElemType) -> IgnoreElem:
    """Create an ignore element according to the type"""
    if isinstance(ignore_elem, ModuleType):
        return IgnoreModule(ignore_elem)  # type: ignore
    if isinstance(ignore_elem, (Path, str)):
        return (
            IgnoreDirname(ignore_elem)  # type: ignore
            if path.isdir(ignore_elem)
            else IgnoreFilename(ignore_elem)  # type: ignore
        )
    if hasattr(ignore_elem, "__code__"):
        return IgnoreFunction(ignore_elem)  # type: ignore
    if not isinstance(ignore_elem, tuple) or len(ignore_elem) != 2:
        raise ValueError(f"Unexpected ignore item: {ignore_elem!r}")
    # is tuple and len == 2
    if hasattr(ignore_elem[0], "__code__") and isinstance(ignore_elem[1], int):
        return IgnoreDecorated(*ignore_elem)  # type: ignore
    # otherwise, the second element should be qualname
    if not isinstance(ignore_elem[1], str):
        raise ValueError(f"Unexpected ignore item: {ignore_elem!r}")

    if isinstance(ignore_elem[0], ModuleType):
        return IgnoreModuleQualname(*ignore_elem)  # type: ignore
    if isinstance(ignore_elem[0], (Path, str)):
        return IgnoreFilenameQualname(*ignore_elem)  # type: ignore
    if ignore_elem[0] is None:
        return IgnoreOnlyQualname(*ignore_elem)

    raise ValueError(f"Unexpected ignore item: {ignore_elem!r}")


class IgnoreList:
    """The ignore list to match the frames to see if they should be ignored"""

    @classmethod
    def create(
        cls,
        ignore: IgnoreType = None,
        ignore_lambda: bool = True,
        ignore_varname: bool = True,
    ) -> "IgnoreList":
        """Create an IgnoreList object

        Args:
            ignore: An element of the ignore list, either
                A module (or filename of a module)
                A tuple of module (or filename) and qualified name
                A function
                A tuple of function and number of decorators
            ignore_lambda: whether ignore lambda functions
            ignore_varname: whether the calls from this package

        Returns:
            The IgnoreList object
        """
        ignore = ignore or []
        if not isinstance(ignore, list):
            ignore = [ignore]

        ignore_list = [
            IgnoreStdlib(  # type: ignore
                sysconfig.get_python_lib(standard_lib=True)
            )
        ]  # type: List[IgnoreElem]
        if ignore_varname:
            ignore_list.append(create_ignore_elem(sys.modules[__package__]))
        if ignore_lambda:
            ignore_list.append(create_ignore_elem((None, "*<lambda>")))
        for ignore_elem in ignore:
            ignore_list.append(create_ignore_elem(ignore_elem))

        return cls(ignore_list)  # type: ignore

    def __init__(self, ignore_list: List[IgnoreElemType]) -> None:
        self.ignore_list = ignore_list
        debug_ignore_frame(">>> IgnoreList initiated <<<")

    def nextframe_to_check(
        self, frame_no: int, frameinfos: List[inspect.FrameInfo]
    ) -> int:
        """Find the next frame to check

        In modst cases, the next frame to check is the next adjacent frame.
        But for IgnoreDecorated, the next frame to check should be the next
        `ignore[1]`th frame.

        Args:
            frame_no: The index of current frame to check
            frameinfos: The frame info objects

        Returns:
            A number for Next `N`th frame to check. 0 if no frame matched.
        """
        for ignore_elem in self.ignore_list:
            matched = ignore_elem.match(frame_no, frameinfos)  # type: ignore
            if matched and isinstance(ignore_elem, IgnoreDecorated):
                debug_ignore_frame(
                    f"Ignored by {ignore_elem!r}", frameinfos[frame_no]
                )
                return ignore_elem.n_decor + 1

            if matched:
                debug_ignore_frame(
                    f"Ignored by {ignore_elem!r}", frameinfos[frame_no]
                )
                return 1
        return 0

    def get_frame(self, frame_no: int) -> FrameType:
        """Get the right frame by the frame number

        Args:
            frame_no: The index of the frame to get

        Returns:
            The desired frame

        Raises:
            VarnameRetrievingError: if any exceptions raised during the process.
        """
        try:
            # since this function will be called by APIs
            # so we should skip that
            frames = inspect.getouterframes(sys._getframe(2), 0)
            i = 0

            while i < len(frames):
                nextframe = self.nextframe_to_check(i, frames)
                # ignored
                if nextframe > 0:
                    i += nextframe
                    continue

                frame_no -= 1
                if frame_no == 0:
                    debug_ignore_frame("Gotcha!", frames[i])
                    return frames[i].frame

                debug_ignore_frame(
                    f"Skipping ({frame_no - 1} more to skip)", frames[i]
                )
                i += 1

        except Exception as exc:
            from .utils import VarnameRetrievingError

            raise VarnameRetrievingError from exc

        return None  # pragma: no cover
