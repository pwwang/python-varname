import sys
from varname import varname

def func():
    # ignore all calls named _func*
    return varname(ignore=(sys.modules[__name__], 'func'))

# func2.__qualname__ == func.__qualname__ == 'func'
func2 = func

def func():
    return func2()

def func3():
    return func()
