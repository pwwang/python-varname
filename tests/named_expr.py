"""Contains code that is only importable with Python >= 3.8."""

from varname import varname

def function():
    return varname(named_expr=True), varname(named_expr=False)

a = [b := function(), c := function()]
