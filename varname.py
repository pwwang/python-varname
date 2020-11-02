"""Dark magics about variable name in python"""
import ast
import dis
import sys
import warnings
from typing import Union, Tuple, Any, Optional, Type, List
from types import FrameType, CodeType
from collections import namedtuple as standard_namedtuple
from functools import lru_cache

import executing

__version__ = "0.5.1"
__all__ = [
    "VarnameRetrievingError", "varname", "will",
    "inject", "nameof", "namedtuple", "Wrapper"
]

NodeType = Type[ast.AST]

class VarnameRetrievingError(Exception):
    """When failed to retrieve the varname"""

def varname(caller: int = 1, raise_exc: bool = True) -> Optional[str]:
    """Get the variable name that assigned by function/class calls

    Args:
        caller: The call stack index, indicating where this function
            is called relative to where the variable is finally retrieved
        raise_exc: Whether we should raise an exception if failed
            to retrieve the name.

    Returns:
        The variable name, or `None` when `raise_exc` is `False` and
            we failed to retrieve the variable name.

    Raises:
        VarnameRetrievingError: When there is invalid variable used on the
            left of the assign node. (e.g: `a.b = func()`) or
            when we are unable to retrieve the variable name and `raise_exc`
            is set to `True`.

        UserWarning: When there are multiple target
            in the assign node. (e.g: `a = b = func()`, in such a case,
            `b == 'a'`, may not be the case you want)
    """
    node = _get_node(caller, raise_exc=raise_exc)
    if not node:
        if raise_exc:
            raise VarnameRetrievingError("Unable to retrieve the ast node.")
        return None

    node = _lookfor_parent_assign(node)
    if not node:
        if raise_exc:
            raise VarnameRetrievingError(
                'Failed to retrieve the variable name.'
            )
        return None

    # Need to actually check that there's just one
    # give warnings if: a = b = func()
    if len(node.targets) > 1:
        warnings.warn("Multiple targets in assignment, variable name "
                      "on the very left will be used.",
                      UserWarning)
    target = node.targets[0]
    return _node_name(target)

def will(caller: int = 1, raise_exc: bool = True) -> Optional[str]:
    """Detect the attribute name right immediately after a function call.

    Examples:
        >>> class AwesomeClass:
        >>>     def __init__(self):
        >>>         self.will = None

        >>>     def permit(self):
        >>>         self.will = will()
        >>>         if self.will == 'do':
        >>>             # let self handle do
        >>>             return self
        >>>         raise AttributeError(
        >>>             'Should do something with AwesomeClass object'
        >>>         )

        >>>     def do(self):
        >>>         if self.will != 'do':
        >>>             raise AttributeError("You don't have permission to do")
        >>>         return 'I am doing!'

        >>> awesome = AwesomeClass()
        >>> # AttributeError: You don't have permission to do
        >>> awesome.do()
        >>> # AttributeError: Should do something with AwesomeClass object
        >>> awesome.permit()
        >>> awesome.permit().do() == 'I am doing!'

    Args:
        caller: At which stack this function is called.
        raise_exc: Raise exception we failed to detect

    Returns:
        The attribute name right after the function call
        If there is no attribute attached and `raise_exc` is `False`

    Raises:
        VarnameRetrievingError: When `raise_exc` is `True` and we failed to
            detect the attribute name (including not having one)
    """
    node = _get_node(caller, raise_exc=raise_exc)
    if not node:
        if raise_exc:
            raise VarnameRetrievingError("Unable to retrieve the frame.")
        return None

    # try to get node inst.attr from inst.attr()
    node = node.parent

    # see test_will_fail
    if not isinstance(node, ast.Attribute):
        if raise_exc:
            raise VarnameRetrievingError(
                "Function `will` has to be called within "
                "a method/property of a class."
            )
        return None
    # ast.Attribute
    return node.attr

def inject(obj: object) -> object:
    """Inject attribute `__varname__` to an object

    Examples:
        >>> class MyList(list):
        >>>     pass

        >>> a = varname.inject(MyList())
        >>> b = varname.inject(MyList())

        >>> a.__varname__ == 'a'
        >>> b.__varname__ == 'b'

        >>> a == b

        >>> # other methods not affected
        >>> a.append(1)
        >>> b.append(1)
        >>> a == b

    Args:
        obj: An object that can be injected

    Raises:
        VarnameRetrievingError: When `__varname__` is unable to
            be set as an attribute

    Returns:
        The object with __varname__ injected
    """
    vname = varname()
    try:
        setattr(obj, '__varname__', vname)
    except AttributeError:
        raise VarnameRetrievingError('Unable to inject __varname__.') from None
    return obj


def nameof(var, *more_vars, # pylint: disable=unused-argument
           caller: int = 1,
           full: bool = False) -> Union[str, Tuple[str]]:
    """Get the names of the variables passed in

    Examples:
        >>> a = 1
        >>> nameof(a) # 'a'

        >>> b = 2
        >>> nameof(a, b) # ('a', 'b')

        >>> x = lambda: None
        >>> x.y = 1
        >>> nameof(x.y) # 'x.y'

    Args:
        var: The variable to retrieve the name of
        *more_vars: Other variables to retrieve the names of
        caller: The depth of the caller (this function) is called.
            This is useful if you want to wrap this function.
        full: Whether report the full path of the variable.
            For example: `nameof(a.b.c, full=True)` give you `a.b.c`
            instead of `c`

    Returns:
        The names of variables passed in

    Raises:
        VarnameRetrievingError: When the callee's node cannot be retrieved or
            trying to retrieve the full name of non attribute series calls.
    """
    node = _get_node(caller - 1, raise_exc=True)
    if not node:
        # only works with nameof(a) or nameof(a.b)
        # no keyword arguments is supposed to be passed in
        # that means we cannot retrieve the full name without
        # soucecode available and you can't wrap this function in such a case
        if not more_vars:
            return _bytecode_nameof(caller + 1)
        raise VarnameRetrievingError("Unable to retrieve callee's node.")

    ret: List[str] = []
    for arg in node.args:
        if not full or isinstance(arg, ast.Name):
            ret.append(_node_name(arg))
        else:
            # traverse the node to get the full name: nameof(a.b.c)
            # arg:
            # Attribute(value=Attribute(value=Name(id='a', ctx=Load()),
            #                           attr='b',
            #                           ctx=Load()),
            #           attr='c',
            #           ctx=Load())
            full_name = []
            while not isinstance(arg, ast.Name):
                if not isinstance(arg, ast.Attribute):
                    raise VarnameRetrievingError(
                        'Can only retrieve full names of '
                        '(chained) attribute calls by nameof.'
                    )
                full_name.append(arg.attr)
                arg = arg.value
            # now it is an ast.Name
            full_name.append(arg.id)
            ret.append('.'.join(reversed(full_name)))

    return ret[0] if not more_vars else tuple(ret)

def namedtuple(*args, **kwargs) -> type:
    """A shortcut for namedtuple

    You don't need to specify the typename, which will be fetched from
    the variable name.

    So instead of:
        >>> from collections import namedtuple
        >>> Name = namedtuple('Name', ['first', 'last'])

    You can do:
        >>> from varname import namedtuple
        >>> Name = namedtuple(['first', 'last'])

    Args:
        *args: arguments for `collections.namedtuple` except `typename`
        **kwargs: keyword arguments for `collections.namedtuple`
            except `typename`

    Returns:
        The namedtuple you desired.
    """
    typename = varname(raise_exc=True)
    return standard_namedtuple(typename, *args, **kwargs)

class Wrapper:
    """A wrapper with ability to retrieve the variable name

    Examples:
        >>> foo = Wrapper(True)
        >>> # foo.name == 'foo'
        >>> # foo.value == True

        >>> val = {}
        >>> bar = Wrapper(val)
        >>> # bar.name == 'bar'
        >>> # bar.value is val

    Args:
        value: The value to be wrapped
        raise_exc: Whether to raise exception when varname is failed to retrieve

    Attributes:
        name: The variable name to which the instance is assigned
        value: The value this wrapper wraps
    """

    def __init__(self, value: Any, raise_exc: bool = True):
        self.name = varname(raise_exc=raise_exc)
        self.value = value

    def __str__(self) -> str:
        return repr(self.value)

    def __repr__(self) -> str:
        return (f"<{self.__class__.__name__} "
                f"(name={self.name!r}, value={self.value!r})>")

def _get_frame(caller: int) -> FrameType:
    """Get the frame at `caller` depth"""
    try:
        return sys._getframe(caller + 1)
    except Exception as exc:
        raise VarnameRetrievingError from exc

def _get_node(caller: int, raise_exc: bool = True) -> Optional[NodeType]:
    """Try to get node from the executing object.

    This can fail when a frame is failed to retrieve.
    One case should be when python code is executed in
    R pacakge `reticulate`, where only first frame is kept.

    When the node can not be retrieved, try to return the first statement.
    """
    try:
        frame = _get_frame(caller + 2)
    except VarnameRetrievingError:
        return None

    exet = executing.Source.executing(frame)

    if exet.node:
        return exet.node

    if exet.source.text and exet.source.tree and raise_exc:
        raise VarnameRetrievingError(
            "Couldn't retrieve the call node. "
            "This may happen if you're using some other AST magic at the "
            "same time, such as pytest, ipython, macropy, or birdseye."
        )

    return None

def _lookfor_parent_assign(node: NodeType) -> Optional[ast.Assign]:
    """Look for an ast.Assign node in the parents"""
    while hasattr(node, 'parent'):
        node = node.parent

        if isinstance(node, ast.Assign):
            return node
    return None

def _node_name(node: NodeType) -> str:
    """Get the node node name.

    Raises VarnameRetrievingError when failed
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr

    raise VarnameRetrievingError(
        f"Can only get name of a variable or attribute, "
        f"not {ast.dump(node)}"
    )

def _bytecode_nameof(caller: int = 1) -> str:
    """Bytecode version of nameof as a fallback"""
    frame = _get_frame(caller)
    source = frame.f_code.co_filename
    return _bytecode_nameof_cached(frame.f_code, frame.f_lasti, source)

@lru_cache()
def _bytecode_nameof_cached(code: CodeType, offset: int, source: str) -> str:
    """Cached Bytecode version of nameof

    We are trying this version only when the soucecode is unavisible. In most
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
        if source == '<stdin>':
            raise VarnameRetrievingError(
                "Are you trying to call nameof in REPL/python shell? "
                "In such a case, nameof can only be called with single "
                "argument and no keyword arguments."
            )
        if source == '<string>':
            raise VarnameRetrievingError(
                "Are you trying to call nameof from evaluation? "
                "In such a case, nameof can only be called with single "
                "argument and no keyword arguments."
            )
        raise VarnameRetrievingError("Did you call nameof in a weird way? ")

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
