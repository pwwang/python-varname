"""Dark magics about variable names in python"""
# pylint: disable=unused-import
from .utils import (
    config,
    VarnameRetrievingError,
    QualnameNonUniqueError,
    MultiTargetAssignmentWarning,
    MaybeDecoratedFunctionWarning
)
from .core import varname, nameof, will

__version__ = "0.6.0"
