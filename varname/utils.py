"""Some internal utilities for varname


Attributes:

    IgnoreElemType: The type for ignore elements
    IgnoreType: The type for the ignore argument
    MODULE_IGNORE_ID_NAME: The name of the ignore id injected to the module.
        Espectially for modules that can't be retrieved by
        `inspect.getmodule(frame)`
"""
import sys
import dis
import ast
import inspect
from os import path
from functools import lru_cache
from types import ModuleType, FunctionType, CodeType, FrameType
from typing import Optional, Tuple, Union, List

from executing import Source

IgnoreElemType = Union[
    # module
    ModuleType,
    # filename of a module
    str,
    FunctionType,
    # the module (filename) and qualname
    # If module is None, then all qualname matches the 2nd element
    # will be ignored. Used to ignore <lambda> internally
    Tuple[Optional[Union[ModuleType, str]], str],
    # Function and number of its decorators
    Tuple[FunctionType, int]
]
IgnoreType = Union[IgnoreElemType, List[IgnoreElemType]]

MODULE_IGNORE_ID_NAME = '__varname_ignore_id__'

class config: # pylint: disable=invalid-name
    """Global configurations for varname"""
    debug = False

class VarnameRetrievingError(Exception):
    """When failed to retrieve the varname"""

class QualnameNonUniqueError(Exception):
    """When a qualified name is used as an ignore element but references to
    multiple objects in a module"""

class MaybeDecoratedFunctionWarning(Warning):
    """When a suspecious decorated function used as ignore function directly"""

class MultiTargetAssignmentWarning(Warning):
    """When varname tries to retrieve variable name in
    a multi-target assignment"""

@lru_cache()
def cached_getmodule(codeobj: CodeType):
    """Cached version of inspect.getmodule"""
    return inspect.getmodule(codeobj)

def get_node(
        frame: int,
        ignore: Optional[IgnoreType] = None,
        raise_exc: bool = True
) -> Optional[ast.AST]:
    """Try to get node from the executing object.

    This can fail when a frame is failed to retrieve.
    One case should be when python code is executed in
    R pacakge `reticulate`, where only first frame is kept.

    When the node can not be retrieved, try to return the first statement.
    """
    from .ignore import IgnoreList
    ignore = IgnoreList.create(ignore)
    try:
        frame = ignore.get_frame(frame)
    except VarnameRetrievingError:
        return None

    exect = Source.executing(frame)

    if exect.node:
        return exect.node

    if exect.source.text and exect.source.tree and raise_exc:
        raise VarnameRetrievingError(
            "Couldn't retrieve the call node. "
            "This may happen if you're using some other AST magic at the "
            "same time, such as pytest, ipython, macropy, or birdseye."
        )

    return None

def lookfor_parent_assign(node: ast.AST) -> Optional[ast.Assign]:
    """Look for an ast.Assign node in the parents"""
    while hasattr(node, 'parent'):
        node = node.parent

        if isinstance(node, (ast.AnnAssign, ast.Assign)):
            return node
    return None

def node_name(node: ast.AST) -> Optional[Union[str, Tuple[Union[str, tuple]]]]:
    """Get the node node name.

    Raises VarnameRetrievingError when failed
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, (ast.List, ast.Tuple)):
        return tuple(node_name(elem) for elem in node.elts)

    raise VarnameRetrievingError(
        f"Can only get name of a variable or attribute, "
        f"not {ast.dump(node)}"
    )

def bytecode_nameof(frame: int = 1) -> str:
    """Bytecode version of nameof as a fallback"""
    from .ignore import IgnoreList
    frame = IgnoreList.create(None).get_frame(frame)
    return _bytecode_nameof_cached(frame.f_code, frame.f_lasti)

@lru_cache()
def _bytecode_nameof_cached(code: CodeType, offset: int) -> str:
    """Cached Bytecode version of nameof

    We are trying this version only when the sourcecode is unavisible. In most
    cases, this will happen when user is trying to run a script in REPL/
    python shell, with `eval`, or other circumstances where the code is
    manipulated to run but sourcecode is not available.
    """
    instructions = list(dis.get_instructions(code))
    (current_instruction_index, current_instruction), = (
        (index, instruction)
        for index, instruction in enumerate(instructions)
        if instruction.offset == offset
    )

    if current_instruction.opname not in ("CALL_FUNCTION", "CALL_METHOD"):
        raise VarnameRetrievingError("Did you call nameof in a weird way?")

    name_instruction = instructions[
        current_instruction_index - 1
    ]

    if not name_instruction.opname.startswith("LOAD_"):
        raise VarnameRetrievingError("Argument must be a variable or attribute")

    name = name_instruction.argrepr
    if not name.isidentifier():
        raise VarnameRetrievingError(
            f"Found the variable name {name!r} which is obviously wrong. "
            "This may happen if you're using some other AST magic at the "
            "same time, such as pytest, ipython, macropy, or birdseye."
        )

    return name

def attach_ignore_id_to_module(module: ModuleType) -> None:
    """Attach the ignore id to module

    This is useful when a module cannot be retrieved by frames using
    `inspect.getmodule`, then we can use this id, which will exist in
    `frame.f_globals` to check if the module matches in ignore.

    Do it only when the __file__ is not avaiable or does not exist for
    the module. Since this probably means the source is not avaiable and
    `inspect.getmodule` would not work
    """
    module_file = getattr(module, '__file__', None)
    if module_file is not None and path.isfile(module_file):
        return
    # or it's already been set
    if hasattr(module, MODULE_IGNORE_ID_NAME):
        return

    setattr(module, MODULE_IGNORE_ID_NAME, f'<varname-ignore-{id(module)})')


def frame_matches_module_by_ignore_id(
        frame: FrameType,
        module: ModuleType
) -> bool:
    """Check if the frame is from the module by ignore id"""
    ignore_id_attached = getattr(module, MODULE_IGNORE_ID_NAME, object())
    ignore_id_from_frame = frame.f_globals.get(MODULE_IGNORE_ID_NAME, object())
    return ignore_id_attached == ignore_id_from_frame

@lru_cache()
def check_qualname_by_source(
        source: Source,
        modname: str,
        qualname: str
) -> None:
    """Check if a qualname in module is unique"""
    if not source.tree:
        # no way to check it, skip
        return
    nobj = list(source._qualnames.values()).count(qualname)
    if nobj > 1:
        raise QualnameNonUniqueError(
            f"Qualname {qualname!r} in "
            f"{modname!r} refers to multiple objects."
        )

def debug_ignore_frame(
        msg: str,
        frameinfo: Optional[inspect.FrameInfo] = None
) -> None:
    """Print the debug message for a given frame info object

    Args:
        msg: The debugging message
        frameinfo: The FrameInfo object for the frame
    """
    if not config.debug:
        return
    if frameinfo is not None:
        msg = (f'{msg} [In {frameinfo.function!r} at '
               f'{frameinfo.filename}:{frameinfo.lineno}]')
    sys.stderr.write(f'[{__name__}] DEBUG: {msg}\n')
