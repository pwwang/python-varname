import textwrap
from functools import singledispatch

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

def test_argname_pure_eval():
    def func(a):
        return argname(a)
    x = 1
    funcs = [func]
    name = funcs[0](x)
    assert name == 'x'

def test_argname_eval():
    x = 1
    with pytest.warns(UserWarning, match="Cannot evaluate node"):
        name = (lambda a: argname(a))(x)
    assert name == 'x'

def test_argname_no_pure_eval(no_pure_eval):
    def func(a):
        return argname(a)
    x = 1
    funcs = [func]

    with pytest.warns(UserWarning, match="'pure_eval' is not installed"):
        name = funcs[0](x)
    assert name == 'x'


def test_argname_non_argument():
    x = 1
    y = lambda: argname(x)
    with pytest.raises(ValueError,
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
    with pytest.raises(ValueError,
                       match="Arguments of 'argname' must be"):
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

def test_argname_star_args():
    def func(*args, **kwargs):
        return argname(args, kwargs)

    x = y = z = 1
    arg_source, kwarg_source = func(x, y, c=z)

    assert arg_source == ('x', 'y')
    assert kwarg_source == {'c': 'z'}

    def func(*args, **kwargs):
        return argname(args, kwargs, vars_only=False)

    arg_source, kwarg_source = func(1+2, 2+3, c=4*5)
    assert arg_source == ('1+2', '2+3')
    assert kwarg_source == {'c': '4*5'}

def test_argname_star_args_individual():
    def func(*args, **kwargs):
        return argname(args[1]), argname(kwargs['c'])

    x = y = z = 1
    second_name = func(x, y, c=z)
    assert second_name == ('y', 'z')

    m = [1]
    def func(*args, **kwargs):
        return argname(m[0])

    with pytest.raises(ValueError, match="'m' is not an argument"):
        func()

    def func(a, *args, **kwargs):
        return argname(a[0])
    with pytest.raises(ValueError, match="'a' is not a positional argument"):
        func(m)

    n = {'e': 1}
    def func(a, *args, **kwargs):
        return argname(a['e'])
    with pytest.raises(ValueError, match="'a' is not a keyword argument"):
        func(n)

    def func(*args, **kwargs):
        return argname([args][0])
    with pytest.raises(ValueError, match="to be a variable"):
        func()

    def func(*args, **kwargs):
        return argname(args[1+1])
    with pytest.raises(ValueError, match="to be a constant"):
        func(x, y, z)

    def func(*args, **kwargs):
        return argname(args[x])
    with pytest.raises(ValueError, match="to be a constant"):
        func(x, y, z)

def test_argname_argname_node_na():
    source = textwrap.dedent(f"""\
        from varname import argname
        def func(a):
            return argname(a)

        x = 1
        print(func(x))
    """)
    code = compile(source, '<string343>', 'exec')
    with pytest.raises(
            VarnameRetrievingError,
            match="The source code of 'argname' calling is not available"
    ):
        exec(code)

def test_argname_func_node_na():
    def func(a):
        return argname(a)

    with pytest.raises(
            VarnameRetrievingError,
            match="The source code of 'argname' calling is not available"
    ):
        exec('x=1; func(x)')

def test_argname_func_na():
    def func(a):
        return argname(a)

    with pytest.raises(
            VarnameRetrievingError,
            match="The source code of 'argname' calling is not available"
    ):
        exec('x=1; func(x)')

def test_argname_wrapper():

    def decorator(f):
        def wrapper(arg, *more_args):
            return f(arg, *more_args, frame=2)

        return wrapper

    argname2 = decorator(argname)

    def func(a, b):
        return argname2(a, b)

    x = y = 1
    names = func(x, y)
    assert names == ('x', 'y')

def test_argname_varpos_arg():
    def func(a, *args, **kwargs):
        return argname(kwargs, a, *args)

    x = y = z = 1
    names = func(x, y, kw=z)
    assert names == ({'kw': 'z'}, 'x', 'y')

    names = func(x)
    assert names == ({}, 'x')

def test_argname_nosuch_varpos_arg():
    def func(a, *args):
        another = []
        return argname(a, *another)

    x = y = 1
    with pytest.raises(
            ValueError,
            match="No such variable positional argument"
    ):
        func(x, y)

def test_argname_target_arg():
    def func(a, b):
        return argname(a)

    x = 1
    names = func(x, 1)
    assert names == 'x'

def test_argname_singledispatched():
    # GH53
    @singledispatch
    def add(a, b):
        aname = argname(a, b, func=add.dispatch(object))
        return aname + (1, ) # distinguish

    @add.register(int)
    def add_int(a, b):
        aname = argname(a, b, func=add_int)
        return aname + (2, )

    @add.register(str)
    def add_str(a, b):
        aname = argname(a, b, dispatch=str)
        return aname + (3, )

    x = y = 1
    out = add(x, y)
    assert out == ('x', 'y', 2)

    t = s = 'a'
    out = add(t, s)
    assert out == ('t', 's', 3)

    p = q = 1.2
    out = add(p, q)
    assert out == ('p', 'q', 1)

def test_argname2():

    def func(a, b, c, d=4):
        return argname2('c', 'b')

    x = y = z = 1
    names = func(x, y, z)
    assert names == ('z', 'y')

    def func2(a, b, c, d=4):
        return argname2('b')

    names2 = func2(x, y, z)
    assert names2 == 'y'

    def func3(e=1):
        return argname2('e')

    names3 = func3(z)
    assert names3 == 'z'

    def func4(a, b=1):
        return argname2('a', 'b')
    names4 = func4(y, b=x)
    assert names4 == ('y', 'x')

def test_argname2_func_na():
    def func(a):
        return argname2('a')

    with pytest.raises(
            VarnameRetrievingError,
            match="Cannot retrieve the node where the function is called"
    ):
        exec('x=1; func(x)')

def test_argname2_singledispatched():
    # GH53
    @singledispatch
    def add(a, b):
        aname = argname2('a', 'b', func=add.dispatch(object))
        return aname + (1, ) # distinguish

    @add.register(int)
    def add_int(a, b):
        aname = argname2('a', 'b', func=add_int)
        return aname + (2, )

    @add.register(str)
    def add_str(a, b):
        aname = argname2('a', 'b', dispatch=str)
        return aname + (3, )

    x = y = 1
    out = add(x, y)
    assert out == ('x', 'y', 2)

    t = s = 'a'
    out = add(t, s)
    assert out == ('t', 's', 3)

    p = q = 1.2
    out = add(p, q)
    assert out == ('p', 'q', 1)

def test_argname2_nosucharg():

    def func(a):
        return argname2('x')

    x = 1
    with pytest.raises(ValueError):
        func(x)

def test_argname2_subscript_star():

    def func1(*args, **kwargs):
        return argname2('args[0]', 'kwargs[x]')

    def func2(*args, **kwargs):
        return argname2('*args')

    x = y = 1
    out = func1(y, x=x)
    assert out == ('y', 'x')

    out = func2(x, y)
    assert out == ('x', 'y')

def test_argname2_nonvar():

    def func(x):
        return argname2('x')

    with pytest.raises(NonVariableArgumentError):
        func(1)

def test_argname2_frame_error():
    def func(x):
        return argname2('x', frame=2)

    with pytest.raises(ValueError, match="is not a valid argument"):
        func(1)

def test_argname2_ignore():
    def target(*args):
        return argname2('*args', ignore=(wrapper, 0))

    def wrapper(*args):
        return target(*args)

    x = y = 1
    out = wrapper(x, y)
    assert out == ('x', 'y')
