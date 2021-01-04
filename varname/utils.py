"""Some internal utilities for varname"""
import dis
from functools import lru_cache
import ast
from types import CodeType
from typing import Optional, Tuple, Union

from executing import Source

from .ignore import IgnoreList, IgnoreType

class config: # pylint: disable=invalid-name
    """Global configurations for varname"""
    debug = False

class VarnameRetrievingError(Exception):
    """When failed to retrieve the varname"""

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
    ignore = IgnoreList.create(ignore)
    try:
        frame = ignore.get_frame(frame)
    except VarnameRetrievingError:
        return None

    exect = Source.executing(frame)

    if exect.node:
        return exect.node
    print(exect.node, '|', exect.source.text, '//', exect.source.tree)
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
