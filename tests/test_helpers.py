import sys

import pytest
from varname import *
from varname.helpers import *


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


def test_register_to_function():
    @register
    def func():
        return __varname__

    f = func()
    assert f == "f"

    # wrapped with other function
    @register(frame=2)
    def func1():
        return __varname__

    def func2():
        return func1()

    f = func2()
    assert f == "f"

    # with ignore
    def func3():
        return func4()

    @register(ignore=[(sys.modules[__name__], func3.__qualname__)])
    def func4():
        return __varname__

    f = func3()
    assert f == "f"
