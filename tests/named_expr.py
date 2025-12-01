"""Contains code that is only importable with Python >= 3.8."""

from varname import varname


def function():
    return varname()


a = [b := function(), c := function()]
