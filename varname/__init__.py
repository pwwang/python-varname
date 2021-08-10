"""Dark magics about variable names in python"""
# pylint: disable=unused-import
from .utils import (
    config,
    VarnameRetrievingError,
    ImproperUseError,
    QualnameNonUniqueError,
    NonVariableArgumentError,
    MultiTargetAssignmentWarning,
    MaybeDecoratedFunctionWarning,
)
from .core import varname, nameof, will, argname, argname2

__version__ = "0.7.2"
