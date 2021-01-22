import sys
from varname import varname

def func():
    # all calls from this module will be ignored
    return varname(ignore=sys.modules[__name__])

def func2():
    return func()

def func3():
    return func2()
