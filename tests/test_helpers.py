import sys

import pytest
from varname import varname
from varname.utils import MaybeDecoratedFunctionWarning, VarnameRetrievingError
from varname.helpers import Wrapper, debug, jsobj, register, exec_code


def test_wrapper():

    val1 = Wrapper(True)
    assert val1.name == "val1"
    assert val1.value is True

    assert str(val1) == "True"
    assert repr(val1) == "<Wrapper (name='val1', value=True)>"

    # wrapped Wrapper
    def wrapped(value):
        return Wrapper(value, frame=2)

    val2 = wrapped(True)
    assert val2.name == "val2"
    assert val2.value is True

    # with ignore
    def wrapped2(value):
        return Wrapper(value, ignore=[wrapped2])

    with pytest.warns(MaybeDecoratedFunctionWarning):
        val3 = wrapped2(True)
    assert val3.name == "val3"
    assert val3.value is True


def test_debug(capsys):
    a = 1
    b = object()
    debug(a)
    assert "DEBUG: a=1\n" == capsys.readouterr().out
    debug(a, b, merge=True)
    assert "DEBUG: a=1, b=<object" in capsys.readouterr().out
    debug(a + a, vars_only=False)
    assert "DEBUG: a + a=2" in capsys.readouterr().out


def test_register_to_class():
    @register
    class Foo:
        def __init__(self, a=1):
            self.a = a

    f = Foo()
    assert f.__varname__ == "f"
    assert f.a == 1

    f2 = Foo(2)
    assert f2.__varname__ == "f2"
    assert f2.a == 2

    def wrapped(foo):
        return foo.__varname__

    @register(
        ignore=[(sys.modules[__name__], wrapped.__qualname__)],
    )
    class Foo:
        def __init__(self):
            ...

    foo = Foo()  # registered with strict=True
    foo = wrapped(foo)
    assert foo == "foo"


def test_jsobj():
    obj = jsobj(a=1, b=2)
    assert obj == {"a": 1, "b": 2}
    assert obj['a'] == 1
    assert obj['b'] == 2

    a = 1
    b = 2
    obj = jsobj(a, b, c=3)
    assert obj == {"a": 1, "b": 2, "c": 3}

    x = lambda: None
    x.b = 2
    obj = jsobj(a, x.b)
    assert obj == {"a": 1, "b": 2}
    obj1 = jsobj(a, x.b, vars_only=False)
    assert obj1 == {"a": 1, "x.b": 2}

    vars_only = 3
    obj2 = jsobj(vars_only, x.b)
    assert obj2 == {"vars_only": 3, "b": 2}
    obj3 = jsobj(vars_only, x.b, vars_only=False)
    assert obj3 == {"vars_only": 3, "x.b": 2}


def test_jsobj_wrapping():
    def myjsobj(*args, **kwargs):
        return jsobj(*args, vars_only=False, frame=2, **kwargs)

    x = lambda: None
    x.b = 2
    obj = myjsobj(x.b)
    assert obj == {"x.b": 2}


def test_register_to_function():
    @register
    def func():
        return __varname__  # noqa # pyright: ignore

    f = func()
    assert f == "f"

    # wrapped with other function
    @register(frame=2)
    def func1():
        return __varname__  # noqa # pyright: ignore

    def func2():
        return func1()

    f = func2()
    assert f == "f"

    # with ignore
    def func3():
        return func4()

    @register(ignore=[(sys.modules[__name__], func3.__qualname__)])
    def func4():
        return __varname__  # noqa # pyright: ignore

    f = func3()
    assert f == "f"


def test_exec_code(tmp_path):
    def func():
        return varname()

    # Normal case works
    f = func()
    assert f == "f"

    code = "f1 = func()"
    with pytest.raises(VarnameRetrievingError):
        exec(code)

    # works
    exec_code(code)

    locs = {"func": func}
    exec_code(code, globals(), locs)
    assert locs["f1"] == "f1"
    del locs["f1"]

    exec_code(code, globals(), locs, sourcefile=tmp_path / "test.py")
    assert locs["f1"] == "f1"
