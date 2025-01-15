"""Dark magics about variable names in python"""

from .utils import (
    config,
    VarnameException,
    VarnameRetrievingError,
    ImproperUseError,
    QualnameNonUniqueError,
    VarnameWarning,
    MultiTargetAssignmentWarning,
    MaybeDecoratedFunctionWarning,
    UsingExecWarning,
)
from .core import varname, will, argname

__version__ = "0.14.0"
