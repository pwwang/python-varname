"""Get the variable name that assigned by function/class calls"""
import ast
import inspect
import warnings
import executing

__version__ = "0.1.5"

VARNAME_INDEX = [-1]

class MultipleTargetAssignmentWarning(Warning):
    """When multiple-target assignment found, i.e. y = x = func()"""

class VarnameRetrievingWarning(Warning):
    """When varname retrieving failed for whatever reason"""

class VarnameRetrievingError(Exception):
    """When failed to retrieve the varname"""

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
    frame = inspect.stack()[caller+1].frame
    node = executing.Source.executing(frame).node
    while hasattr(node, 'parent'):
        node = node.parent

        if isinstance(node, ast.Assign):
            # Need to actually check that there's just one
            if len(node.targets) > 1:
                warnings.warn("Multiple targets in assignment, variable name "
                              "on the very left will be used.",
                              MultipleTargetAssignmentWarning)
            target = node.targets[0]

            # Need to check that it's a variable
            if isinstance(target, ast.Name):
                return target.id

            raise VarnameRetrievingError(
                f"Invaid variable assigned: {ast.dump(target)!r}"
            )

    if raise_exc:
        raise VarnameRetrievingError('Failed to retrieve the variable name.')

    VARNAME_INDEX[0] += 1
    warnings.warn(f"var_{VARNAME_INDEX[0]} used.",
                  VarnameRetrievingWarning)
    return f"var_{VARNAME_INDEX[0]}"

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
    frame = inspect.stack()[caller+1].frame
    source = executing.Source.executing(frame)
    ret = None
    try:
        node = source.node
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

def nameof(*args):
    """Get the names of the variables passed in

    Args:
        *args: A couple of variables passed in

    Returns:
        tuple|str:
    """
    frame = inspect.stack()[1].frame
    exe = executing.Source.executing(frame)

    if not exe.node:
        # we cannot do: assert nameof(a) == 'a' in pytest
        raise VarnameRetrievingError("Callee's node cannot be detected.")

    assert isinstance(exe.node, ast.Call)

    ret = []
    for node in exe.node.args:
        if not isinstance(node, ast.Name):
            raise VarnameRetrievingError("Only variables should "
                                         "be passed to nameof.")
        ret.append(node.id)

    if not ret:
        raise VarnameRetrievingError("At least one variable should be "
                                     "passed to nameof")

    return ret[0] if len(args) == 1 else tuple(ret)

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
