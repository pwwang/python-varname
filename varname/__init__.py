"""Dark magics about variable names in python"""
# pylint: disable=unused-import
from .utils import (
    config,
    VarnameRetrievingError,
    QualnameNonUniqueError,
    NonVariableArgumentError,
    MultiTargetAssignmentWarning,
    MaybeDecoratedFunctionWarning
)
from .core import varname, nameof, will, argname

__version__ = "0.6.3"
