"""Get the variable name that assigned by function/class calls"""
import ast
import dis
import sys
import warnings
from collections import namedtuple as standard_namedtuple
from functools import lru_cache

import executing

__version__ = "0.2.0"

VARNAME_INDEX = [-1]


class MultipleTargetAssignmentWarning(Warning):
    """When multiple-target assignment found, i.e. y = x = func()"""

class VarnameRetrievingWarning(Warning):
    """When varname retrieving failed for whatever reason"""

class VarnameRetrievingError(Exception):
    """When failed to retrieve the varname"""


def _get_frame(caller):
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
        return list(exet.statements)[0]

    return None


def _lookfor_parent_assign(node):
    """Look for an ast.Assign node in the parents"""
    while hasattr(node, 'parent'):
        node = node.parent

        if isinstance(node, ast.Assign):
            return node
    return None

def _lookfor_child_nameof(node):
    """Look for ast.Call with func=Name(id='nameof',...)"""
    # pylint: disable=too-many-return-statements
    if isinstance(node, ast.Call):
        # if node.func.id == 'nameof':
        #     return node

        # We want to support alias for nameof, i.e. nameof2
        # Or called like: varname.nameof(test)
        # If all args are ast.Name, then if must be alias of nameof
        # Since this is originated from it, and there is no other
        # ast.Call node in args
        if not any(isinstance(arg, ast.Call) for arg in node.args):
            return node

        # print(nameof(test))
        for arg in node.args:
            found = _lookfor_child_nameof(arg)
            if found:
                return found

    elif isinstance(node, ast.Compare):
        # nameof(test) == 'test'
        found = _lookfor_child_nameof(node.left)
        if found:
            return found
        # 'test' == nameof(test)
        for comp in node.comparators:
            found = _lookfor_child_nameof(comp)
            if found:
                return found

    elif isinstance(node, ast.Assert):
        # assert nameof(test) == 'test'
        found = _lookfor_child_nameof(node.test)
        if found:
            return found

    elif isinstance(node, ast.Expr): # pragma: no cover
        # print(nameof(test)) in ipython's forloop
        # issue #5
        found = _lookfor_child_nameof(node.value)
        if found:
            return found

    return None


def varname(caller=1, raise_exc=False):
    """Get the variable name that assigned by function/class calls

    Args:
        caller (int): The call stack index
        raise_exc (bool): Whether we should raise an exception if failed
            to retrieve the name

    Returns:
        str: The variable name, or `var_<index>` if failed

    Raises:
        VarnameRetrievingError: When there is invalid variable used on the
            left of the assign node. (e.g: `a.b = func()`) or
            when we are unable to retrieve the variable name and `raise_exc`
            is set to `True`.

    Warns:
        MultipleTargetAssignmentWarning: When there are multiple target
            in the assign node. (e.g: `a = b = func()`, in such a case,
            `b == 'a'`, may not be the case you want)
    """
    node = _get_node(caller)
    if not node:
        if raise_exc:
            raise VarnameRetrievingError("Unable to retrieve the ast node.")
        VARNAME_INDEX[0] += 1
        warnings.warn(f"var_{VARNAME_INDEX[0]} used.",
                      VarnameRetrievingWarning)
        return f"var_{VARNAME_INDEX[0]}"

    node = _lookfor_parent_assign(node)
    if not node:
        if raise_exc:
            raise VarnameRetrievingError(
                'Failed to retrieve the variable name.'
            )
        VARNAME_INDEX[0] += 1
        warnings.warn(f"var_{VARNAME_INDEX[0]} used.", VarnameRetrievingWarning)
        return f"var_{VARNAME_INDEX[0]}"

    # Need to actually check that there's just one
    # give warnings if: a = b = func()
    if len(node.targets) > 1:
        warnings.warn("Multiple targets in assignment, variable name "
                      "on the very left will be used.",
                      MultipleTargetAssignmentWarning)
    target = node.targets[0]

    # must be a variable
    if isinstance(target, ast.Name):
        return target.id

    raise VarnameRetrievingError(
        f"Invaid variable assigned: {ast.dump(target)!r}"
    )

def will(caller=1, raise_exc=False):
    """Detect the attribute name right immediately after a function call.

    Examples:
        ```python
        def i_will():
            will = varname.will()
            func = lambda: 0
            func.will = will
            return func

        func = i_will().abc

        # func.will == 'abc'
        ```

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

    ret = None
    try:
        # have to be used in a call
        assert isinstance(node, (ast.Attribute, ast.Call)), (
            "Invalid use of function `will`"
        )
        node = node.parent
    except (AssertionError, AttributeError):
        pass
    else:
        if isinstance(node, ast.Attribute):
            ret = node.attr

        if not ret and raise_exc:
            raise VarnameRetrievingError('Unable to retrieve the '
                                         'next attribute name')

    return ret

def inject(obj):
    """Inject attribute `__varname__` to an object

    Args:
        obj: An object that can be injected

    Warns:
        VarnameRetrievingWarning: When `__varname__` already exists

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

def nameof(*args, caller=1):
    """Get the names of the variables passed in

    Args:
        *args: A couple of variables passed in

    Returns:
        tuple|str: The names of variables passed in
    """
    node = _get_node(caller - 1)
    node = _lookfor_child_nameof(node)
    if not node:
        if len(args) == 1:
            return _bytecode_nameof(caller + 1)
        raise VarnameRetrievingError("Unable to retrieve callee's node.")

    ret = []
    for arg in node.args:
        if not isinstance(arg, ast.Name):
            raise VarnameRetrievingError("Only variables should "
                                         "be passed to nameof.")
        ret.append(arg.id)

    if not ret:
        raise VarnameRetrievingError("At least one variable should be "
                                     "passed to nameof")

    return ret[0] if len(args) == 1 else tuple(ret)


def _bytecode_nameof(caller=1):
    frame = _get_frame(caller)
    return _bytecode_nameof_cached(frame.f_code, frame.f_lasti)


@lru_cache()
def _bytecode_nameof_cached(code, offset):
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
    return name_instruction.argrepr


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
    """
    typename = varname(raise_exc=True)
    return standard_namedtuple(typename, *args, **kwargs)

class Wrapper:
    """A wrapper with ability to retrieve the variable name"""

    def __init__(self, value):
        self.name = varname()
        self.value = value

    def __str__(self):
        return repr(self.value)

    def __repr__(self):
        return (f"<{self.__class__.__name__} "
                f"(name={self.name!r}, value={self.value!r})>")
