"""Dark magics about variable name in python"""
import ast
import dis
import sys
import warnings
from typing import Union, Tuple
from collections import namedtuple as standard_namedtuple
from functools import lru_cache

import executing

__version__ = "0.3.0"

VARNAME_INDEX = [-1]

class MultipleTargetAssignmentWarning(Warning):
    """When multiple-target assignment found, i.e. y = x = func()"""

class VarnameRetrievingWarning(Warning):
    """When varname retrieving failed for whatever reason"""

class VarnameRetrievingError(Exception):
    """When failed to retrieve the varname"""

def varname(caller: int = 1, raise_exc: bool = False) -> str:
    """Get the variable name that assigned by function/class calls

    Args:
        caller (int): The call stack index, indicating where this function
            is called relative to where the variable is finally retrieved
        raise_exc (bool): Whether we should raise an exception if failed
            to retrieve the name.

    Returns:
        str|None: The variable name, or
            `var_<index>` (will be deprecated in `v0.4.0`) if failed.
            It returns `None` when `raise_exc` is `False` and
            we failed to retrieve the variable name.

    Raises:
        VarnameRetrievingError: When there is invalid variable used on the
            left of the assign node. (e.g: `a.b = func()`) or
            when we are unable to retrieve the variable name and `raise_exc`
            is set to `True`.

    Warns:
        MultipleTargetAssignmentWarning: When there are multiple target
            in the assign node. (e.g: `a = b = func()`, in such a case,
            `b == 'a'`, may not be the case you want)
        VarnameRetrievingWarning: When `var_0` and alike returned.
            This will be deprecated in `v0.4.0`
    """
    node = _get_node(caller)
    if not node:
        if raise_exc:
            raise VarnameRetrievingError("Unable to retrieve the ast node.")
        VARNAME_INDEX[0] += 1
        warnings.warn(f"var_{VARNAME_INDEX[0]} used, "
                      "which will be deprecated in v0.4.0",
                      VarnameRetrievingWarning)
        return f"var_{VARNAME_INDEX[0]}"

    node = _lookfor_parent_assign(node)
    if not node:
        if raise_exc:
            raise VarnameRetrievingError(
                'Failed to retrieve the variable name.'
            )
        VARNAME_INDEX[0] += 1
        warnings.warn(f"var_{VARNAME_INDEX[0]} used, "
                      "which will be deprecated in v0.4.0",
                      VarnameRetrievingWarning)
        return f"var_{VARNAME_INDEX[0]}"

    # Need to actually check that there's just one
    # give warnings if: a = b = func()
    if len(node.targets) > 1:
        warnings.warn("Multiple targets in assignment, variable name "
                      "on the very left will be used.",
                      MultipleTargetAssignmentWarning)
    target = node.targets[0]
    return _node_name(target)

def will(caller: int = 1, raise_exc: bool = False) -> str:
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
        caller (int): At which stack this function is called.
        raise_exc (bool): Raise exception we failed to detect

    Returns:
        str: The attribute name right after the function call
        None: If there is no attribute attached and `raise_exc` is `False`

    Raises:
        VarnameRetrievingError: When `raise_exc` is `True` and we failed to
            detect the attribute name (including not having one)
    """
    node = _get_node(caller)
    if not node:
        if raise_exc:
            raise VarnameRetrievingError("Unable to retrieve the frame.")
        return None

    # try to get not inst.attr from inst.attr()
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

def inject(obj: any) -> any:
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
        obj: The object with __varname__ injected
    """
    vname = varname()
    try:
        setattr(obj, '__varname__', vname)
    except AttributeError:
        raise VarnameRetrievingError('Unable to inject __varname__.')
    return obj


# _caller is only used for test purposes
# or unless one wants to wrap this function
def nameof(*args, _caller: int = 1) -> Union[str, Tuple[str]]:
    """Get the names of the variables passed in

    Examples:
        >>> a = 1
        >>> aname = nameof(a)
        >>> # aname == 'a

        >>> b = 2
        >>> aname, bname = nameof(a, b)
        >>> # aname == 'a', bname == 'b'

    Args:
        *args: A couple of variables passed in

    Returns:
        tuple|str: The names of variables passed in
    """
    node = _get_node(_caller - 1)
    if not node:
        if len(args) == 1:
            return _bytecode_nameof(_caller + 1)
        raise VarnameRetrievingError("Unable to retrieve callee's node.")

    ret = []
    for arg in node.args:
        ret.append(_node_name(arg))

    if not ret:
        raise VarnameRetrievingError("At least one variable should be "
                                     "passed to nameof")

    return ret[0] if len(args) == 1 else tuple(ret)

def namedtuple(*args, **kwargs):
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
    """
    typename: str = varname(raise_exc=True)
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


    Attributes:
        name (str): The variable name to which the instance is assigned
        value (any): The value this wrapper wraps
    """

    def __init__(self, value: any, raise_exc: bool = False):
        self.name: str = varname(raise_exc=raise_exc)
        self.value: any = value

    def __str__(self) -> str:
        return repr(self.value)

    def __repr__(self) -> str:
        return (f"<{self.__class__.__name__} "
                f"(name={self.name!r}, value={self.value!r})>")

def _get_frame(caller):
    """Get the frame at `caller` depth"""
    try:
        return sys._getframe(caller + 1)
    except Exception as exc:
        raise VarnameRetrievingError from exc

def _get_node(caller):
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

    if exet.source.text and exet.source.tree:
        raise VarnameRetrievingError(
            "Couldn't retrieve the call node. "
            "This may happen if you're using some other AST magic at the "
            "same time, such as pytest, ipython, macropy, or birdseye."
        )

    return None

def _lookfor_parent_assign(node):
    """Look for an ast.Assign node in the parents"""
    while hasattr(node, 'parent'):
        node = node.parent

        if isinstance(node, ast.Assign):
            return node
    return None

def _node_name(node):
    """Get the node node name"""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr

    raise VarnameRetrievingError(
        f"Can only get name of a variable or attribute, "
        f"not {ast.dump(node)}"
    )

def _bytecode_nameof(caller=1):
    """Bytecode version of nameof as a fallback"""
    frame = _get_frame(caller)
    return _bytecode_nameof_cached(frame.f_code, frame.f_lasti)

@lru_cache()
def _bytecode_nameof_cached(code, offset):
    """Cached Bytecode version of nameof"""
    instructions = list(dis.get_instructions(code))
    (current_instruction_index, current_instruction), = (
        (index, instruction)
        for index, instruction in enumerate(instructions)
        if instruction.offset == offset
    )

    if current_instruction.opname not in ("CALL_FUNCTION", "CALL_METHOD"):
        raise VarnameRetrievingError("Did you call nameof in a weird way?")

    name_instruction = instructions[current_instruction_index - 1]
    if not name_instruction.opname.startswith("LOAD_"):
        raise VarnameRetrievingError("Argument must be a variable or attribute")

    name: str = name_instruction.argrepr
    if not name.isidentifier():
        raise VarnameRetrievingError(
            f"Found the variable name {name!r} which is obviously wrong. "
            "This may happen if you're using some other AST magic at the "
            "same time, such as pytest, ipython, macropy, or birdseye."
        )

    return name
