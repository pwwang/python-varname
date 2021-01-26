import pytest
from varname import *

def test_argname():

    def func(a, b, c, d=4):
        return argname(c, b)

    x = y = z = 1
    names = func(x, y, z)
    assert names == ('z', 'y')

    def func2(a, b, c, d=4):
        return argname(b)

    names2 = func2(x, y, z)
    assert names2 == 'y'

    def func3(e=1):
        return argname(e)

    names3 = func3(z)
    assert names3 == 'z'

    def func4(a, b=1):
        return argname(a, b)
    names4 = func4(y, b=x)
    assert names4 == ('y', 'x')

def test_argname_lambda():
    func = lambda a, b, c, d=4: argname(b)
    x = y = z = 1
    names = func(x, y, z)
    assert names == 'y'

def test_argname_argname_node_fail(no_getframe):
    def func(a, b, c, d=4):
        return argname(b)
    x = y = z = 1
    with pytest.raises(VarnameRetrievingError,
                       match="Unable to retrieve the call node of 'argname'"):
        func(x, y, z)

def test_argname_non_argument():
    x = 1
    y = lambda: argname(x)
    with pytest.raises(VarnameRetrievingError,
                       match="No value passed for argument 'x'"):
        y()

def test_argname_non_variable():
    def func(a, b, c, d=4):
        return argname(b)

    with pytest.raises(NonVariableArgumentError,
                       match=r"is not a variable"):
        func(1,1,1)

def test_argname_argname_argument_non_variable():
    def func(a, b, c, d=4):
        return argname(1)

    x = y = z = 1
    with pytest.raises(VarnameRetrievingError,
                       match="Arguments of 'argname' must be argument variables"):
        func(x, y, z)

def test_argname_funcnode_not_call():
    x = 1
    class Foo:
        @property
        def prop(self):
            y = argname(x)

    foo = Foo()
    with pytest.raises(VarnameRetrievingError,
                       match="Are you using 'argname' inside a function"):
        foo.prop

def test_argname_get_source():
    def func(a, b=1):
        return argname(a, vars_only=False)

    name = func(1+2)
    assert name == '1+2'
