import textwrap
from functools import singledispatch

import pytest
from varname import *


def test_argname():
    def func(a, b, c, d=4):
        return argname("c", "b")

    x = y = z = 1
    names = func(x, y, z)
    assert names == ("z", "y")

    names = func(x, "a", 1)
    assert names == ('1', "'a'")

    def func2(a, b, c, d=4):
        return argname("b")

    names2 = func2(x, y, z)
    assert names2 == "y"

    def func3(e=1):
        return argname("e")

    names3 = func3(z)
    assert names3 == "z"

    def func4(a, b=1):
        return argname("a", "b")

    names4 = func4(y, b=x)
    assert names4 == ("y", "x")

def test_argname2():
    def func(a, b, c, d=4):
        return argname2("c", "b")

    x = y = z = 1
    with pytest.warns(DeprecationWarning):
        names = func(x, y, z)
    assert names == ("z", "y")

    def func2(a, b, c, d=4):
        return argname2("b")

    with pytest.warns(DeprecationWarning):
        names2 = func2(x, y, z)
    assert names2 == "y"

    def func3(e=1):
        return argname2("e")

    with pytest.warns(DeprecationWarning):
        names3 = func3(z)
    assert names3 == "z"

    def func4(a, b=1):
        return argname2("a", "b")

    with pytest.warns(DeprecationWarning):
        names4 = func4(y, b=x)
    assert names4 == ("y", "x")


def test_argname_lambda():
    func = lambda a, b, c, d=4: argname("b")
    x = y = z = 1
    names = func(x, y, z)
    assert names == "y"


def test_argname_pure_eval():
    def func(a):
        return argname("a")

    x = 1
    funcs = [func]
    name = funcs[0](x)
    assert name == "x"


def test_argname_eval():
    x = 1
    with pytest.warns(UsingExecWarning, match="Cannot evaluate node"):
        name = (lambda a: argname("a"))(x)
    assert name == "x"


def test_argname_no_pure_eval(no_pure_eval):
    def func(a):
        return argname("a")

    x = 1
    funcs = [func]

    with pytest.warns(UsingExecWarning, match="'pure_eval' is not installed"):
        name = funcs[0](x)
    assert name == "x"


def test_argname_non_argument():
    x = 1
    y = lambda: argname("x")
    with pytest.raises(ImproperUseError, match="'x' is not a valid argument"):
        y()


def test_argname_non_variable():
    def func(a, b, c, d=4):
        return argname("b")

    with pytest.raises(ImproperUseError, match=r"is not a variable"):
        func(1, {1}, 1)


def test_argname_argname_argument_non_variable():
    def func(a, b, c, d=4):
        return argname(1)

    x = y = z = 1
    with pytest.raises(TypeError, match="expected string or bytes-like object"):
        func(x, y, z)


def test_argname_funcnode_not_call():
    x = 1

    class Foo:

        def __neg__(self):
            return argname("self")

    foo = Foo()
    with pytest.raises(
        VarnameRetrievingError,
        match="Cannot reconstruct ast.Call node from UnaryOp",
    ):
        -foo


def test_argname_get_source():
    def func(a, b=1):
        return argname("a", vars_only=False)

    name = func(1 + 2)
    assert name == "1 + 2"


def test_argname_star_args():
    def func(*args, **kwargs):
        return argname("args", "kwargs")

    x = y = z = 1
    arg_source, kwarg_source = func(x, y, c=z)

    assert arg_source == ("x", "y")
    assert kwarg_source == {"c": "z"}

    def func(*args, **kwargs):
        return argname("args", "kwargs", vars_only=False)

    arg_source, kwarg_source = func(1 + 2, 2 + 3, c=4 * 5)
    assert arg_source == ("1 + 2", "2 + 3")
    assert kwarg_source == {"c": "4 * 5"}


def test_argname_star_args_individual():
    def func(*args, **kwargs):
        return argname("args[1]"), argname("kwargs[c]")

    x = y = z = 1
    second_name = func(x, y, c=z)
    assert second_name == ("y", "z")

    m = [1]

    def func(*args, **kwargs):
        return argname("m[0]")

    with pytest.raises(ImproperUseError, match="'m' is not a valid argument"):
        func()

    def func(a, *args, **kwargs):
        return argname("a[0]")

    with pytest.raises(
        ImproperUseError, match="`a` is not a positional argument"
    ):
        func(m)

    n = {"e": 1}

    def func(a, *args, **kwargs):
        return argname('a["e"]')

    with pytest.raises(ImproperUseError, match="`a` is not a keyword argument"):
        func(n)

    def func(*args, **kwargs):
        return argname("[args][0]")

    with pytest.raises(ImproperUseError, match="is not a valid argument"):
        func()

    def func(*args, **kwargs):
        return argname("args[1 + 1]")

    with pytest.raises(
        ImproperUseError, match="`args` is not a keyword argument"
    ):
        func(x, y, z)

    def func(*args, **kwargs):
        return argname("args[x]")

    with pytest.raises(
        ImproperUseError, match="`args` is not a keyword argument."
    ):
        func(x, y, z)


def test_argname_argname_node_na():
    source = textwrap.dedent(
        f"""\
        from varname import argname
        def func(a):
            return argname(a)

        x = 1
        print(func(x))
    """
    )
    code = compile(source, "<string343>", "exec")
    with pytest.raises(
        VarnameRetrievingError,
        match="Cannot retrieve the node where the function is called",
    ):
        exec(code)


def test_argname_func_node_na():
    def func(a):
        return argname("a")

    with pytest.raises(
        VarnameRetrievingError,
        match="Cannot retrieve the node where the function is called",
    ):
        exec("x=1; func(x)")


def test_argname_func_na():
    def func(a):
        return argname("a")

    with pytest.raises(
        VarnameRetrievingError,
        match="The source code of 'argname' calling is not available",
    ):
        exec("x=1; func(x)")


def test_argname_wrapper():
    def decorator(f):
        def wrapper(arg, *more_args):
            return f(arg, *more_args, frame=2)

        return wrapper

    argname3 = decorator(argname)

    def func(a, b):
        return argname3("a", "b")

    x = y = 1
    names = func(x, y)
    assert names == ("x", "y")


def test_argname_varpos_arg():
    def func(a, *args, **kwargs):
        return argname("kwargs", "a", "*args")

    x = y = z = 1
    names = func(x, y, kw=z)
    assert names == ({"kw": "z"}, "x", "y")

    names = func(x)
    assert names == ({}, "x")


def test_argname_nosuch_varpos_arg():
    def func(a, *args):
        another = []
        return argname("a", "*another")

    x = y = 1
    with pytest.raises(
        ImproperUseError, match="'another' is not a valid argument"
    ):
        func(x, y)


def test_argname_target_arg():
    def func(a, b):
        return argname("a")

    x = 1
    names = func(x, 1)
    assert names == "x"


def test_argname_singledispatched():
    # GH53
    @singledispatch
    def add(a, b):
        aname = argname("a", "b", func=add.dispatch(object))
        return aname + (1,)  # distinguish

    @add.register(int)
    def add_int(a, b):
        aname = argname("a", "b", func=add_int)
        return aname + (2,)

    @add.register(str)
    def add_str(a, b):
        aname = argname("a", "b", dispatch=str)
        return aname + (3,)

    x = y = 1
    out = add(x, y)
    assert out == ("x", "y", 2)

    t = s = "a"
    out = add(t, s)
    assert out == ("t", "s", 3)

    p = q = 1.2
    out = add(p, q)
    assert out == ("p", "q", 1)


def test_argname_func_na():
    def func(a):
        return argname("a")

    with pytest.raises(
        VarnameRetrievingError,
        match="Cannot retrieve the node where the function is called",
    ):
        exec("x=1; func(x)")


def test_argname_singledispatched():
    # GH53
    @singledispatch
    def add(a, b):
        aname = argname("a", "b", func=add.dispatch(object))
        return aname + (1,)  # distinguish

    @add.register(int)
    def add_int(a, b):
        aname = argname("a", "b", func=add_int)
        return aname + (2,)

    @add.register(str)
    def add_str(a, b):
        aname = argname("a", "b", dispatch=str)
        return aname + (3,)

    x = y = 1
    out = add(x, y)
    assert out == ("x", "y", 2)

    t = s = "a"
    out = add(t, s)
    assert out == ("t", "s", 3)

    p = q = 1.2
    out = add(p, q)
    assert out == ("p", "q", 1)


def test_argname_nosucharg():
    def func(a):
        return argname("x")

    x = 1
    with pytest.raises(ImproperUseError, match="'x' is not a valid argument"):
        func(x)


def test_argname_subscript_star():
    def func1(*args, **kwargs):
        return argname("args[0]", "kwargs[x]")

    def func2(*args, **kwargs):
        return argname("*args")

    x = y = 1
    out = func1(y, x=x)
    assert out == ("y", "x")

    out = func2(x, y)
    assert out == ("x", "y")


def test_argname_nonvar():
    def func(x):
        return argname("x")

    with pytest.raises(ImproperUseError):
        func({1})


def test_argname_frame_error():
    def func(x):
        return argname("x", frame=2)

    with pytest.raises(ImproperUseError, match="'x' is not a valid argument"):
        func(1)


def test_argname_ignore():
    def target(*args):
        return argname("*args", ignore=(wrapper, 0))

    def wrapper(*args):
        return target(*args)

    x = y = 1
    out = wrapper(x, y)
    assert out == ("x", "y")


def test_argname_attribute_item():
    class A:
        def __init__(self):
            self.__dict__["meta"] = {}

        def __getattr__(self, name):
            return argname("name")

        def __setattr__(self, name, value) -> None:
            self.__dict__["meta"]["name"] = argname("name")
            self.__dict__["meta"]["name2"] = argname("name", vars_only=False)
            self.__dict__["meta"]["value"] = argname("value")

        def __getitem__(self, name):
            return argname("name")

        def __setitem__(self, name, value) -> None:
            self.__dict__["meta"]["name"] = argname("name")
            self.__dict__["meta"]["name2"] = argname("name", vars_only=False)
            self.__dict__["meta"]["value"] = argname("value")


    a = A()
    out = a.x
    assert out == "'x'"

    a.__getattr__("x")
    assert out == "'x'"

    a.y = 1
    assert a.meta["name"] == "'y'"
    assert a.meta["name2"] == "'y'"
    assert a.meta["value"] == "1"

    a.__setattr__("y", 1)
    assert a.meta["name"] == "'y'"
    assert a.meta["name2"] == "'y'"
    assert a.meta["value"] == "1"

    out = a[1]
    assert out == "1"

    a[1] = 2
    assert a.meta["name"] == "1"
    assert a.meta["name2"] == "1"
    assert a.meta["value"] == "2"

    with pytest.raises(ImproperUseError):
        a.x = a.y = 1


def test_argname_compare():
    class A:
        def __init__(self):
            self.meta = None

        def __eq__(self, other):
            self.meta = argname("other")
            return True

        def __lt__(self, other):
            self.meta = argname("other")
            return True

        def __gt__(self, other):
            self.meta = argname("other")
            return True

    a = A()
    a == 1
    assert a.meta == '1'

    a < 2
    assert a.meta == '2'

    a > 3
    assert a.meta == '3'


def test_argname_binop():
    class A:
        def __init__(self):
            self.meta = None

        def __add__(self, other):
            self.meta = argname("other")
            return 1

    a = A()
    out = a + 1
    assert out == 1
    assert a.meta == '1'


def test_argname_wrong_frame():
    def func(x):
        return argname("x", func=property.getter)

    with pytest.raises(
        ImproperUseError,
        match="Have you specified the right `frame` or `func`",
    ):
        func(1)
