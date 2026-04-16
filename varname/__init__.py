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
from .core import varname, nameof, will, argname

__version__ = "0.15.1"

__all__ = [
    "varname",
    "nameof",
    "will",
    "argname",
    "config",
    "VarnameException",
    "VarnameRetrievingError",
    "ImproperUseError",
    "QualnameNonUniqueError",
    "VarnameWarning",
    "MultiTargetAssignmentWarning",
    "MaybeDecoratedFunctionWarning",
    "UsingExecWarning",
]
