"""Get the variable name that assigned by function/class calls"""
import ast
import inspect
import warnings
import executing

__version__ = "0.1.0"

VARNAME_INDEX = [-1]

class VarnameAssignedToInvalidVariable(Exception):
    """If left-hand side is not a variable"""

class MultipleTargetAssignmentWarning(Warning):
    """When multiple-target assignment found, i.e. y = x = func()"""

class UnableToRetrieveVarnameWarning(Warning):
    """When multiple-target assignment found, i.e. y = x = func()"""

def varname(caller=1):
    """Get the variable name that assigned by function/class calls
    @params:
        caller (int): The call stack index
    @returns:
        (str): The variable name, or `var_<index>` if failed
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

            raise VarnameAssignedToInvalidVariable(
                f"Invaid variable assigned: {ast.dump(target)!r}"
            )

    VARNAME_INDEX[0] += 1
    warnings.warn(f"var_{VARNAME_INDEX[0]} used.",
                  UnableToRetrieveVarnameWarning)
    return f"var_{VARNAME_INDEX[0]}"
