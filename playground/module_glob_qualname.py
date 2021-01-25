import sys
from varname import varname

def _func():
    # ignore all calls named _func*
    return varname(ignore=(sys.modules[__name__], '_func*'))

def _func2():
    return _func()

def func3():
    return _func2()
