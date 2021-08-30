"""Dark magics about variable names in python"""
# pylint: disable=unused-import
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
from .core import varname, nameof, will, argname, argname2

__version__ = "0.8.1"
