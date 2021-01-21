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

Any frames in `varname` , and frames of any expressions like
<listcomp/dictcomp/setcomp/genexpr/lambda> are ignored by default.

Attributes:

    MODULE_IGNORE_ID_NAME: The name of the ignore id injected to the module.
        Espectially for modules that can't be retrieved by
        `inspect.getmodule(frame)`
"""
import sys
import inspect
import distutils.sysconfig as sysconfig
import warnings
from os import path
from functools import lru_cache
from fnmatch import fnmatch
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from types import FrameType, ModuleType, FunctionType

from executing import Source

from .utils import (
    IgnoreElemType,
    IgnoreType,
    cached_getmodule,
    QualnameNonUniqueError,
    MaybeDecoratedFunctionWarning
)

MODULE_IGNORE_ID_NAME = '__varname_ignore_id__'

def debug_ignore_frame(msg: str,
                       frameinfo: Optional[inspect.FrameInfo] = None) -> None:
    """Print the debug message for a given frame info object

    Args:
        msg: The debugging message
        frameinfo: The FrameInfo object for the frame
    """
    from .utils import config
    if not config.debug:
        return
    if frameinfo is not None:
        msg = (f'{msg} [In {frameinfo.function!r} at '
               f'{frameinfo.filename}:{frameinfo.lineno}]')
    sys.stderr.write(f'[{__name__}] DEBUG: {msg}\n')

class IgnoreElem(ABC):
    """An element of the ignore list"""

    def __init__(self, ignore: IgnoreElemType) -> None:
        self.ignore = ignore

    @abstractmethod
    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        """Whether the frame matches the ignore element"""

    @abstractmethod
    def __repr__(self) -> str:
        """Representation of the element"""

class IgnoreModule(IgnoreElem):
    """Ignore calls from a module or its submodules"""

    def __init__(self, ignore: ModuleType) -> None:
        super().__init__(ignore)
        modfile = getattr(self.ignore, '__file__', None)
        if not modfile or not path.isfile(modfile):
            setattr(self.ignore, MODULE_IGNORE_ID_NAME,
                    f'<varname-ignore-{id(self.ignore)}>')

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        frame = frameinfos[frame_no].frame
        module = cached_getmodule(frame.f_code)
        if module:
            return (module.__name__ == self.ignore.__name__ or
                    module.__name__.startswith(f'{self.ignore.__name__}.'))

        return (getattr(self.ignore, MODULE_IGNORE_ID_NAME, object()) ==
                frame.f_globals.get(MODULE_IGNORE_ID_NAME, object()))

    def __repr__(self):
        return f'<IgnoreModule({self.ignore.__name__!r})>'

class IgnoreFilename(IgnoreElem):
    """Ignore calls from a module by matching its filename"""

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        frame = frameinfos[frame_no].frame

        # in case of symbolic links
        return (path.realpath(frame.f_code.co_filename) ==
                path.realpath(self.ignore))

    def __repr__(self):
        return f'<IgnoreFilename({self.ignore!r})>'

class IgnoreDirname(IgnoreElem):
    """Ignore calls from modules inside a directory

    Currently used internally to ignore calls from standard libraries."""

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        frame = frameinfos[frame_no].frame

        if not self.ignore.endswith(path.sep):
            self.ignore = f'{self.ignore}{path.sep}'
        return path.realpath(frame.f_code.co_filename).startswith(
            path.realpath(self.ignore)
        )

    def __repr__(self):
        return f'<IgnoreDirname({self.ignore!r})>'

class IgnoreFunction(IgnoreElem):
    """Ignore a non-decorated function"""
    def __init__(self, ignore: FunctionType) -> None:
        super().__init__(ignore)
        if (
                '<locals>' in ignore.__qualname__ or # without functools.wraps
                ignore.__name__ != ignore.__code__.co_name
        ):
            warnings.warn(
                f'You asked varname to ignore function {ignore.__name__!r}, '
                'which may be decorated. If it is not intended, you may need '
                'to ignore all intemediated frames or with a tuple of '
                'the function and the number of its decorators.',
                MaybeDecoratedFunctionWarning
            )

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        frame = frameinfos[frame_no].frame
        return frame.f_code == self.ignore.__code__

    def __repr__(self):
        return f'<IgnoreFunction({self.ignore.__name__})>'

class IgnoreDecorated(IgnoreElem):
    """Ignore a decorated function"""
    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        try:
            frame = frameinfos[frame_no + self.ignore[1]].frame
        except IndexError:
            return False

        return frame.f_code == self.ignore[0].__code__

    def __repr__(self):
        return f'<IgnoreDecorated({self.ignore[0].__name__}, {self.ignore[1]})>'

class IgnoreModuleQualname(IgnoreElem):
    """Ignore calls by qualified name in the module"""
    def __init__(self, ignore: Tuple[ModuleType, str]) -> None:
        super().__init__(ignore)

        # check uniqueness of qualname
        self.qname_checked = False
        modfile = getattr(self.ignore[0], '__file__', None)
        if not modfile or not path.isfile(modfile):
            setattr(self.ignore[0], MODULE_IGNORE_ID_NAME,
                    f'<varname-ignore-{id(self.ignore)}>')
        if modfile:
            source = Source.for_filename(modfile, self.ignore[0].__dict__)
            self._check_qualname_by_source(source)
            self.qname_checked = True

    @staticmethod
    @lru_cache()
    def _source_from_frame(frame: FrameType) -> Source:
        """Get source object from the given frame"""
        return Source.for_frame(frame)

    def _check_qualname_by_source(self, source: Source) -> None:
        """Check if qualname references to multiple objects"""
        if not source.tree:
            # there is no way to check
            return
        nobj = list(source._qualnames.values()).count(self.ignore[1])
        # don't check for non-existence, as it could contain wildcards
        if nobj > 1:
            raise QualnameNonUniqueError(
                f"Qualname {self.ignore[1]!r} in "
                f"{self.ignore[0].__name__!r} refers to multiple objects."
            )

    @lru_cache()
    def _check_qualname_by_frame(self, frame: FrameType) -> None:
        """Check if qualname references to multiple objects by given frame"""
        source = IgnoreModuleQualname._source_from_frame(frame)
        self._check_qualname_by_source(source)

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        frame = frameinfos[frame_no].frame
        module = cached_getmodule(frame.f_code)
        # Return earlier to avoid qualname uniqueness check
        if module and module != self.ignore[0]:
            return False

        if not module and (
                getattr(self.ignore[0], MODULE_IGNORE_ID_NAME, object()) !=
                frame.f_globals.get(MODULE_IGNORE_ID_NAME, object())
        ):
            return False

        if not self.qname_checked: # // todo: coverage
            self._check_qualname_by_frame(frame)
            self.qname_checked = True

        source = IgnoreModuleQualname._source_from_frame(frame)
        return fnmatch(
            source.code_qualname(frame.f_code),
            self.ignore[1]
        )

    def __repr__(self) -> str:
        return ('<IgnoreModuleQualname'
                f'({self.ignore[0].__name__!r}, {self.ignore[1]})>')

class IgnoreFilenameQualname(IgnoreElem):
    """Ignore calls with given qualname in the module with the filename"""

    # check qualname uniqueness in this as well?

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        frame = frameinfos[frame_no].frame

        return (
            path.realpath(frame.f_code.co_filename) ==
            path.realpath(self.ignore[0]) and
            fnmatch(
                Source.for_frame(frame).code_qualname(frame.f_code),
                self.ignore[1]
            )
        )

    def __repr__(self) -> str:
        return f'<IgnoreFilenameQualname({self.ignore[0]!r}, {self.ignore[1]})>'

class IgnoreOnlyQualname(IgnoreElem):
    """Ignore calls that match the given qualname, across all frames."""

    def match(self, frame_no: int, frameinfos: List[inspect.FrameInfo]) -> bool:
        frame = frameinfos[frame_no].frame

        # module is None, check qualname only
        return fnmatch(
            Source.for_frame(frame).code_qualname(frame.f_code),
            self.ignore[1]
        )

    def __repr__(self) -> str:
        return f'<IgnoreOnlyQualname({self.ignore[1]!r})>'

def create_ignore_elem(ignore_elem: IgnoreElemType) -> IgnoreElem:
    """Create an ignore element according to the type"""
    if isinstance(ignore_elem, ModuleType):
        return IgnoreModule(ignore_elem)
    if isinstance(ignore_elem, str):
        return (IgnoreDirname(ignore_elem)
                if path.isdir(ignore_elem)
                else IgnoreFilename(ignore_elem))
    if hasattr(ignore_elem, '__code__'):
        return IgnoreFunction(ignore_elem)
    if not isinstance(ignore_elem, tuple) or len(ignore_elem) != 2:
        raise ValueError(f'Unexpected ignore item: {ignore_elem!r}')
    # is tuple and len == 2
    if hasattr(ignore_elem[0], '__code__') and isinstance(ignore_elem[1], int):
        return IgnoreDecorated(ignore_elem)
    if isinstance(ignore_elem[0], ModuleType):
        return IgnoreModuleQualname(ignore_elem)
    if isinstance(ignore_elem[0], str):
        return IgnoreFilenameQualname(ignore_elem)
    if ignore_elem[0] is None:
        return IgnoreOnlyQualname(ignore_elem)

    raise ValueError(f'Unexpected ignore item: {ignore_elem!r}')

class IgnoreList:
    """The ignore list to match the frames to see if they should be ignored"""
    @classmethod
    def create(cls, ignore: Optional[IgnoreType]) -> "IgnoreList":
        """Create an IgnoreList object

        Args:
            ignore: An element of the ignore list, either
                A module (or filename of a module)
                A tuple of module (or filename) and qualified name
                A function
                A tuple of function and number of decorators

        Returns:
            The IgnoreList object
        """
        ignore = ignore or []
        if not isinstance(ignore, list):
            ignore = [ignore]

        ignore_list = [
            create_ignore_elem(sysconfig.get_python_lib(standard_lib=True)),
            create_ignore_elem(sys.modules[__package__]),
            # Will the following be calls?
            # create_ignore_elem((None, '<listcomp>')),
            # create_ignore_elem((None, '<dictcomp>')),
            # create_ignore_elem((None, '<setcomp>')),
            # create_ignore_elem((None, '<genexpr>')),
            create_ignore_elem((None, r'*<lambda>')),
        ]
        for ignore_elem in ignore:
            ignore_list.append(create_ignore_elem(ignore_elem))

        return cls(ignore_list)

    def __init__(self, ignore_list: List[IgnoreElemType]) -> None:
        self.ignore_list = ignore_list

    def nextframe_to_check(self,
                           frame_no: int,
                           frameinfos: List[inspect.FrameInfo]) -> int:
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
            matched = ignore_elem.match(frame_no, frameinfos)
            if matched and isinstance(ignore_elem, IgnoreDecorated):
                debug_ignore_frame(f'Ignored by {ignore_elem!r}',
                                   frameinfos[frame_no])
                return ignore_elem.ignore[1] + 1

            if matched:
                debug_ignore_frame(f'Ignored by {ignore_elem!r}',
                                   frameinfos[frame_no])
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
                    debug_ignore_frame('Gotcha!', frames[i])
                    return frames[i].frame

                debug_ignore_frame(
                    f'Skipping ({frame_no - 1} more to skip)',
                    frames[i]
                )
                i += 1

        except Exception as exc:
            from .utils import VarnameRetrievingError
            raise VarnameRetrievingError from exc
