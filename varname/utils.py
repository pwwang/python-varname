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
import warnings
import inspect
from os import path
from pathlib import Path
from functools import lru_cache
from types import ModuleType, FunctionType, CodeType, FrameType
from typing import Tuple, Union, List, Mapping, Callable

from executing import Source

IgnoreElemType = Union[
    # module
    ModuleType,
    # filename of a module
    str,
    Path,
    FunctionType,
    # the module (filename) and qualname
    # If module is None, then all qualname matches the 2nd element
    # will be ignored. Used to ignore <lambda> internally
    Tuple[Union[ModuleType, str], str],
    # Function and number of its decorators
    Tuple[FunctionType, int],
]
IgnoreType = Union[IgnoreElemType, List[IgnoreElemType]]

ArgSourceType = Union[ast.AST, str]
ArgSourceType = Union[ArgSourceType, Tuple[ArgSourceType, ...]]
ArgSourceType = Union[ArgSourceType, Mapping[str, ArgSourceType]]

if sys.version_info >= (3, 8):
    ASSIGN_TYPES = (ast.Assign, ast.AnnAssign, ast.NamedExpr)
    AssignType = Union[ASSIGN_TYPES]  # type: ignore
else:  # pragma: no cover
    ASSIGN_TYPES = (ast.Assign, ast.AnnAssign)
    AssignType = Union[ASSIGN_TYPES]  # type: ignore

MODULE_IGNORE_ID_NAME = "__varname_ignore_id__"


class config:  # pylint: disable=invalid-name
    """Global configurations for varname

    Attributes:
        debug: Show debug information for frames being ignored
    """

    debug = False


class VarnameException(Exception):
    """Root exception for all varname exceptions"""


class VarnameRetrievingError(VarnameException):
    """When failed to retrieve the varname"""


class QualnameNonUniqueError(VarnameException):
    """When a qualified name is used as an ignore element but references to
    multiple objects in a module"""


class ImproperUseError(VarnameException):
    """When varname() is improperly used"""


class VarnameWarning(Warning):
    """Root warning for all varname warnings"""


class MaybeDecoratedFunctionWarning(VarnameWarning):
    """When a suspecious decorated function used as ignore function directly"""


class MultiTargetAssignmentWarning(VarnameWarning):
    """When varname tries to retrieve variable name in
    a multi-target assignment"""

class UsingExecWarning(VarnameWarning):
    """When exec is used to retrieve function name for `argname()`"""


@lru_cache()
def cached_getmodule(codeobj: CodeType):
    """Cached version of inspect.getmodule"""
    return inspect.getmodule(codeobj)


def get_node(
    frame: int,
    ignore: IgnoreType = None,
    raise_exc: bool = True,
    ignore_lambda: bool = True,
) -> ast.AST:
    """Try to get node from the executing object.

    This can fail when a frame is failed to retrieve.
    One case should be when python code is executed in
    R pacakge `reticulate`, where only first frame is kept.

    When the node can not be retrieved, try to return the first statement.
    """
    from .ignore import IgnoreList

    ignore = IgnoreList.create(ignore, ignore_lambda=ignore_lambda)
    try:
        frameobj = ignore.get_frame(frame)
    except VarnameRetrievingError:
        return None

    return get_node_by_frame(frameobj, raise_exc)


def get_node_by_frame(frame: FrameType, raise_exc: bool = True) -> ast.AST:
    """Get the node by frame, raise errors if possible"""
    exect = Source.executing(frame)

    if exect.node:
        # attach the frame for better exception message
        # (ie. where ImproperUseError happens)
        exect.node.__frame__ = frame
        return exect.node

    if exect.source.text and exect.source.tree and raise_exc:
        raise VarnameRetrievingError(
            "Couldn't retrieve the call node. "
            "This may happen if you're using some other AST magic at the "
            "same time, such as pytest, ipython, macropy, or birdseye."
        )

    return None


def lookfor_parent_assign(node: ast.AST, strict: bool = True) -> AssignType:
    """Look for an ast.Assign node in the parents"""
    while hasattr(node, "parent"):
        node = node.parent

        if isinstance(node, ASSIGN_TYPES):
            return node

        if strict:
            break
    return None


def node_name(node: ast.AST) -> Union[str, Tuple[Union[str, Tuple], ...]]:
    """Get the node node name.

    Raises ImproperUseError when failed
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, (ast.List, ast.Tuple)):
        return tuple(node_name(elem) for elem in node.elts)

    raise ImproperUseError(
        f"Can only get name of a variable or attribute, "
        f"not {ast.dump(node)}"
    )


@lru_cache()
def bytecode_nameof(code: CodeType, offset: int) -> str:
    """Cached Bytecode version of nameof

    We are trying this version only when the sourcecode is unavisible. In most
    cases, this will happen when user is trying to run a script in REPL/
    python shell, with `eval`, or other circumstances where the code is
    manipulated to run but sourcecode is not available.
    """
    instructions = list(dis.get_instructions(code))
    ((current_instruction_index, current_instruction),) = (
        (index, instruction)
        for index, instruction in enumerate(instructions)
        if instruction.offset == offset
    )

    if current_instruction.opname in ("CALL_FUNCTION_EX", "CALL_FUNCTION_KW"):
        raise VarnameRetrievingError(
            "'nameof' can only be called with a single positional argument "
            "when source code is not avaiable."
        )

    if current_instruction.opname not in ("CALL_FUNCTION", "CALL_METHOD"):
        raise VarnameRetrievingError("Did you call 'nameof' in a weird way?")

    name_instruction = instructions[current_instruction_index - 1]

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
    module_file = getattr(module, "__file__", None)
    if module_file is not None and path.isfile(module_file):
        return
    # or it's already been set
    if hasattr(module, MODULE_IGNORE_ID_NAME):
        return

    setattr(module, MODULE_IGNORE_ID_NAME, f"<varname-ignore-{id(module)})")


def frame_matches_module_by_ignore_id(
    frame: FrameType, module: ModuleType
) -> bool:
    """Check if the frame is from the module by ignore id"""
    ignore_id_attached = getattr(module, MODULE_IGNORE_ID_NAME, object())
    ignore_id_from_frame = frame.f_globals.get(MODULE_IGNORE_ID_NAME, object())
    return ignore_id_attached == ignore_id_from_frame


@lru_cache()
def check_qualname_by_source(
    source: Source, modname: str, qualname: str
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


def debug_ignore_frame(msg: str, frameinfo: inspect.FrameInfo = None) -> None:
    """Print the debug message for a given frame info object

    Args:
        msg: The debugging message
        frameinfo: The FrameInfo object for the frame
    """
    if not config.debug:
        return
    if frameinfo is not None:
        msg = (
            f"{msg} [In {frameinfo.function!r} at "
            f"{frameinfo.filename}:{frameinfo.lineno}]"
        )
    sys.stderr.write(f"[{__package__}] DEBUG: {msg}\n")


def argnode_source(
    source: Source, node: ast.AST, vars_only: bool
) -> Union[str, ast.AST]:
    """Get the source of an argument node

    Args:
        source: The executing source object
        node: The node to get the source from
        vars_only: Whether only allow variables and attributes

    Returns:
        The source of the node (node.id for ast.Name,
            node.attr for ast.Attribute). Or the node itself if the source
            cannot be fetched.
    """
    if vars_only:
        return (
            node.id
            if isinstance(node, ast.Name)
            else node.attr
            if isinstance(node, ast.Attribute)
            else node
        )

    # requires asttokens
    return source.asttokens().get_text(node)


@lru_cache()
def get_argument_sources(
    source: Source,
    node: ast.Call,
    func: Callable,
    vars_only: bool,
) -> Mapping[str, ArgSourceType]:
    """Get the sources for argument from an ast.Call node

    >>> def func(a, b, c, d=4):
    >>>  ...
    >>> x = y = z = 1
    >>> func(y, x, c=z)
    >>> # argument_sources = {'a': 'y', 'b', 'x', 'c': 'z'}
    >>> func(y, x, c=1)
    >>> # argument_sources = {'a': 'y', 'b', 'x', 'c': ast.Num(n=1)}
    """
    # <Signature (a, b, c, d=4)>
    signature = inspect.signature(func, follow_wrapped=False)
    # func(y, x, c=z)
    # ['y', 'x'], {'c': 'z'}
    arg_sources = [
        argnode_source(source, argnode, vars_only)
        for argnode in node.args
    ]
    kwarg_sources = {
        argnode.arg: argnode_source(source, argnode.value, vars_only)
        for argnode in node.keywords
        if argnode.arg is not None
    }
    bound_args = signature.bind_partial(*arg_sources, **kwarg_sources)
    argument_sources = bound_args.arguments
    # see if *args and **kwargs have anything assigned
    # if not, assign () and {} to them
    for parameter in signature.parameters.values():
        if parameter.kind == inspect.Parameter.VAR_POSITIONAL:
            argument_sources.setdefault(parameter.name, ())
        if parameter.kind == inspect.Parameter.VAR_KEYWORD:
            argument_sources.setdefault(parameter.name, {})
    return argument_sources


def get_function_called_argname(frame: FrameType, node: ast.AST) -> Callable:
    """Get the function who called argname"""
    # We need node to be ast.Call
    if not isinstance(node, ast.Call):
        raise VarnameRetrievingError(
            f"Expect an 'ast.Call' node, but got {type(node)!r}. "
            "Are you using 'argname' inside a function?"
        )

    # variable
    if isinstance(node.func, ast.Name):
        func = frame.f_locals.get(
            node.func.id, frame.f_globals.get(node.func.id)
        )
        if func is None:  # pragma: no cover
            # not sure how it would happen but in case
            raise VarnameRetrievingError(
                f"Cannot retrieve the function by {node.func.id!r}."
            )
        return func

    # use pure_eval
    pure_eval_fail_msg = None
    try:
        from pure_eval import Evaluator, CannotEval
    except ImportError:
        pure_eval_fail_msg = "'pure_eval' is not installed."
    else:
        try:
            evaluator = Evaluator.from_frame(frame)
            return evaluator[node.func]
        except CannotEval:
            pure_eval_fail_msg = (
                f"Cannot evaluate node {ast.dump(node.func)} "
                "using 'pure_eval'."
            )

    # try eval
    warnings.warn(
        f"{pure_eval_fail_msg} "
        "Using 'eval' to get the function that calls 'argname'. "
        "Try calling it using a variable reference to the function, or "
        "passing the function to 'argname' explicitly.",
        UsingExecWarning
    )
    expr = ast.Expression(node.func)
    code = compile(expr, "<ast-call>", "eval")
    # pylint: disable=eval-used
    return eval(code, frame.f_globals, frame.f_locals)


def rich_exc_message(msg: str, node: ast.AST, context_lines: int = 4) -> str:
    """Attach the source code from the node to message to
    get a rich message for exceptions

    If package 'rich' is not install or 'node.__frame__' doesn't exist, fall
    to plain message (with basic information), otherwise show a better message
    with full information
    """
    frame = node.__frame__  # type: FrameType
    lineno = node.lineno - 1  # type: int
    col_offset = node.col_offset  # type: int
    filename = frame.f_code.co_filename  # type: str
    try:
        lines, startlineno = inspect.getsourcelines(frame)
    except OSError: # pragma: no cover
        # could not get source code
        return f"{msg}\n"
    startlineno = 0 if startlineno == 0 else startlineno - 1
    line_range = (startlineno + 1, startlineno + len(lines) + 1)

    linenos = tuple(map(str, range(*line_range)))  # type: Tuple[str, ...]
    lineno_width = max(map(len, linenos))  # type: int
    hiline = lineno - startlineno  # type: int
    codes = []  # type: List[str]
    for i, lno in enumerate(linenos):
        if i < hiline - context_lines or i > hiline + context_lines:
            continue
        lno = lno.ljust(lineno_width)
        if i == hiline:
            codes.append(f"  > | {lno}  {lines[i]}")
            codes.append(f"    | {' ' * (lineno_width + col_offset + 2)}^\n")
        else:
            codes.append(f"    | {lno}  {lines[i]}")

    return (
        f"{msg}\n\n"
        f"  {filename}:{lineno+1}:{col_offset+1}\n"
        f"{''.join(codes)}\n"
    )
