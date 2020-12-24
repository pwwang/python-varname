import sys

import pytest
import subprocess
from varname import *
from varname import _get_node

@pytest.fixture
def no_getframe():
    """
    Monkey-patch sys._getframe to fail,
    simulating environments that don't support varname
    """
    def getframe(_context):
        raise ValueError

    orig_getframe = sys._getframe
    try:
        sys._getframe = getframe
        yield
    finally:
        sys._getframe = orig_getframe

@pytest.fixture
def enable_debug():
    import varname as _varname
    _varname.DEBUG = True
    yield
    _varname.DEBUG = False

def test_function():

    def function():
        return varname()

    func = function()
    assert func == 'func'

    func = [function()]
    assert func == ['func']

    func = [function(), function()]
    assert func == ['func', 'func']

    func = (function(), )
    assert func == ('func', )

    func = (function(), function())
    assert func == ('func', 'func')

def test_function_deep():

    def function():
        # I know that at which stack this will be called
        return varname(frame=3)

    def function1():
        return function()

    def function2():
        return function1()

    func = function2()
    assert func == 'func'

def test_class():

    class Foo:
        def __init__(self):
            self.id = varname()
        def copy(self):
            return varname()

    k = Foo()
    assert k.id == 'k'

    k2 = k.copy()
    assert k2 == 'k2'

def test_class_deep():

    class Foo:
        def __init__(self):
            self.id = self.some_internal()

        def some_internal(self):
            return varname(frame=2)

        def copy(self):
            return self.copy_id()

        def copy_id(self):
            return self.copy_id_internal()

        def copy_id_internal(self):
            return varname(frame=3)

    k = Foo()
    assert k.id == 'k'

    k2 = k.copy()
    assert k2 == 'k2'

def test_single_var_lhs_error():
    """Only one variable to receive the name on LHS"""

    def function():
        return varname()

    with pytest.raises(VarnameRetrievingError,
                       match='Expecting a single variable on left-hand side'):
        x, y = function()
    with pytest.raises(VarnameRetrievingError):
        x, y = function(), function()

def test_multi_vars_lhs():
    """Tests multiple variables on the left hand side"""

    def function():
        return varname(multi_vars=True)

    a, b = function()
    assert (a, b) == ('a', 'b')
    [a, b] = function()
    assert (a, b) == ('a', 'b')
    a = function()
    assert a == ('a', )
    # hierarchy
    a, (b, c) = function()
    assert (a, b, c) == ('a', 'b', 'c')
    # with attributes
    x = lambda: 1
    a, (b, x.c) = function()
    assert (a, b, x.c) == ('a', 'b', 'c')

    # Not all LHS are variables
    with pytest.raises(
        VarnameRetrievingError,
        match='Can only get name of a variable or attribute, not Starred'
    ):
        a, *b = function()

def test_raise():

    def get_name(raise_exc):
        return varname(raise_exc=raise_exc)

    with pytest.raises(VarnameRetrievingError):
        get_name(True)

    name = "0"
    # we can't get it in such way.
    name += str(get_name(False))
    assert name == '0None'

def test_multiple_targets():

    def function():
        return varname()

    with pytest.warns(UserWarning, match="Multiple targets in assignment"):
        y = x = function()
    assert y == x == 'y'

def test_unusual():

    def function():
        return varname()

    # something ridiculous
    xyz = function()[-1:]
    assert xyz == 'z'

    x = 'a'
    with pytest.raises(VarnameRetrievingError):
        x += function()
    assert x == 'a'

    # alias
    func = function
    x = func()
    assert x == 'x'

def test_wrapper():

    val1 = Wrapper(True)
    assert val1.name == 'val1'
    assert val1.value is True

    assert str(val1) == 'True'
    assert repr(val1) == "<Wrapper (name='val1', value=True)>"


def test_nameof_pytest_fail():
    with pytest.raises(
        VarnameRetrievingError,
        match="Couldn't retrieve the call node. "
              "This may happen if you're using some other AST magic"
    ):
        assert nameof(nameof) == 'nameof'

def test_varname_from_attributes():
    class C:
        @property
        def var(self):
            return varname()

    c = C()
    v1 = c.var
    assert v1 == 'v1'

def test_will():
    def i_will():
        iwill = will()
        func = lambda: 0
        func.will = iwill
        # return the function itself
        # so that we can retrieve it after the attribute call
        func.abc = func
        return func

    func = i_will().abc
    assert func.will == 'abc'
    assert getattr(func, 'will') == 'abc'

def test_will_deep():

    def get_will():
        return will(2)

    def i_will():
        iwill = get_will()
        func = lambda: 0
        func.will = iwill
        # return the function itself
        # so that we can retrieve it after the attribute call
        func.abc = func
        return func

    func = i_will().abc
    assert func.will == 'abc'

# issue #17
def test_will_property():

    class C:
        def __init__(self):
            self.will = None

        @property
        def iwill(self):
            self.will = will(raise_exc=False)
            return self

        def do(self):
            return 'I will do something'

    c = C()
    c.iwill
    assert c.will is None

    result = c.iwill.do()
    assert c.will == 'do'
    assert result == 'I will do something'


def test_will_method():
    class AwesomeClass:
        def __init__(self):
            self.wills = [None]

        def __call__(self, *_):
            return self

        myself = __call__
        __getattr__ = __call__

        def permit(self, *_):
            self.wills.append(will(raise_exc=False))

            if self.wills[-1] is None:
                raise AttributeError(
                    'Should do something with AwesomeClass object'
                )

            # let self handle do
            return self

        def do(self):
            if self.wills[-1] != 'do':
                raise AttributeError("You don't have permission to do")
            return 'I am doing!'

        __getitem__ = permit

    awesome = AwesomeClass()
    with pytest.raises(AttributeError) as exc:
        awesome.do()
    assert str(exc.value) == "You don't have permission to do"

    with pytest.raises(AttributeError) as exc:
        awesome.permit()
    assert str(exc.value) == 'Should do something with AwesomeClass object'

    # clear wills
    awesome = AwesomeClass()
    ret = awesome.permit().do()
    assert ret == 'I am doing!'
    assert awesome.wills == [None, 'do']

    awesome = AwesomeClass()
    ret = awesome.myself().permit().do()
    assert ret == 'I am doing!'
    assert awesome.wills == [None, 'do']

    awesome = AwesomeClass()
    ret = awesome().permit().do()
    assert ret == 'I am doing!'
    assert awesome.wills == [None, 'do']

    awesome = AwesomeClass()
    ret = awesome.attr.permit().do()
    assert ret == 'I am doing!'
    assert awesome.wills == [None, 'do']

    awesome = AwesomeClass()
    ret = awesome.permit().permit().do()
    assert ret == 'I am doing!'
    assert awesome.wills == [None, 'permit', 'do']

    with pytest.raises(AttributeError) as exc:
        print(awesome[2])
    assert str(exc.value) == 'Should do something with AwesomeClass object'

    ret = awesome[2].do()
    assert ret == 'I am doing!'

def test_will_decorated():

    def return_self(func):
        def wrapper(self, *args, **kwargs):
            func(self, *args, **kwargs)
            return self

        return wrapper

    class Foo:

        def __init__(self):
            self.will = None

        def get_will(self):
            self.will = will(raise_exc=False)
            return self

        @return_self
        def get_will_decor(self):
            self.will = will(2, raise_exc=False)

        def __getattr__(self, name):
            return self.will

    x = Foo().get_will().x
    assert x == 'x'

    x = Foo().get_will_decor().x
    assert x == 'x'


def test_will_fail():

    def get_will(raise_exc):
        return will(raise_exc=raise_exc)

    with pytest.raises(VarnameRetrievingError):
        get_will(True)

    the_will = get_will(False)
    assert the_will is None

def test_frame_fail(no_getframe):
    """Test when failed to retrieve the frame"""
    # Let's monkey-patch inspect.stack to do this
    assert _get_node(1) is None


def test_frame_fail_varname(no_getframe):
    def func(raise_exc):
        return varname(raise_exc=raise_exc)

    with pytest.raises(VarnameRetrievingError):
        a = func(True)

    b = func(False)
    assert b is None


def test_frame_fail_nameof(no_getframe):
    a = 1
    with pytest.raises(VarnameRetrievingError):
        nameof(a)


def test_frame_fail_will(no_getframe):
    def func(raise_exc):
        wil = will(raise_exc=raise_exc)
        ret = lambda: None
        ret.a = 1
        ret.will = wil
        return ret

    with pytest.raises(VarnameRetrievingError):
        func(True).a

    assert func(False).a == 1
    assert func(False).will is None

def test_nameof_full():
    x = lambda: None
    a = x
    a.b = x
    a.b.c = x
    name = nameof(a)
    assert name == 'a'
    name = nameof(a, frame=1)
    assert name == 'a'
    name = nameof(a.b)
    assert name == 'b'
    name = nameof(a.b, full=True)
    assert name == 'a.b'
    name = nameof(a.b.c)
    assert name == 'c'
    name = nameof(a.b.c, full=True)
    assert name == 'a.b.c'

    d = [a, a]
    with pytest.raises(
            VarnameRetrievingError,
            match='Can only retrieve full names of'
    ):
        name = nameof(d[0].b, full=True)

    # we are not able to retreive full names without source code available
    with pytest.raises(
            VarnameRetrievingError,
            match=('Are you trying to call nameof from exec/eval')
    ):
        eval('nameof(a.b, full=False)')


def test_nameof_from_stdin():
    code = ('from varname import nameof; '
            'x = lambda: 0; '
            'x.y = x; '
            'print(nameof(x.y, full=False))')
    p = subprocess.Popen([sys.executable],
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         encoding='utf8')
    out, _ = p.communicate(input=code)
    assert 'Are you trying to call nameof in REPL/python shell' in out

def test_nameof_node_not_retrieved():
    """Test when calling nameof without sourcecode available
    but filename is not <stdin> or <string>"""
    source = ('from varname import nameof; '
              'x = lambda: 0; '
              'x.y = x; '
              'print(nameof(x.y, full=False))')
    code = compile(source, filename="<string2>", mode="exec")
    with pytest.raises(VarnameRetrievingError, match='Source code unavailable'):
        exec(code)

def test_debug(capsys):
    a = 1
    b = object()
    debug(a)
    assert 'DEBUG: a=1\n' == capsys.readouterr().out
    debug(a, b, merge=True)
    assert 'DEBUG: a=1, b=<object' in capsys.readouterr().out

def test_internal_debug(capsys, enable_debug):
    def my_decorator(f):
        def wrapper():
            return f()
        return wrapper

    @my_decorator
    def foo1():
        return foo2()

    @my_decorator
    def foo2():
        return foo3()

    @my_decorator
    def foo3():
        return varname(
            frame=3,
            ignore=[(
                sys.modules[__name__],
                "test_internal_debug.<locals>.my_decorator.<locals>.wrapper"
            )]
        )

    x = foo1()
    assert x == 'x'
    msgs = capsys.readouterr().err.splitlines()
    assert "Skipping frame from varname [In 'varname'" in msgs[0]
    assert "Skipping (2 more to skip) [In 'foo3'" in msgs[1]
    assert "Ignored [In 'wrapper'" in msgs[2]
    assert "Skipping (1 more to skip) [In 'foo2'" in msgs[3]
    assert "Ignored [In 'wrapper'" in msgs[4]
    assert "Skipping (0 more to skip) [In 'foo1'" in msgs[5]
    assert "Ignored [In 'wrapper'" in msgs[6]
    assert "Gotcha! [In 'test_internal_debug'" in msgs[7]

def test_register_to_class():

    @register
    class Foo:
        def __init__(self, a=1):
            self.a = a

    f = Foo()
    assert f.__varname__ == 'f'
    assert f.a == 1

    f2 = Foo(2)
    assert f2.__varname__ == 'f2'
    assert f2.a == 2

def test_register_to_function():

    @register
    def func():
        return __varname__

    f = func()
    assert f == 'f'

    # wrapped with other function
    @register(frame=2)
    def func1():
        return __varname__

    def func2():
        return func1()
    f = func2()
    assert f == 'f'

def test_type_anno_varname():

    class Foo:
        def __init__(self):
            self.id = varname()

    foo: Foo = Foo()
    assert foo.id == 'foo'

def test_generic_type_varname():
    import typing
    from typing import Generic, TypeVar

    T = TypeVar("T")

    class Foo(Generic[T]):
        def __init__(self):
            self.id = varname(ignore=[typing])
    foo = Foo[int]()
    assert foo.id == 'foo'

    bar:Foo = Foo[str]()
    assert bar.id == 'bar'

    baz = Foo()
    assert baz.id == 'baz'

def test_async_varname():

    import asyncio

    def run_async(coro):
        if sys.version_info < (3, 7):
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(coro)
        else:
            return asyncio.run(coro)

    async def func():
        return varname(
            ignore=[
                asyncio,
                (sys.modules[__name__], 'test_async_varname.<locals>.run_async')
            ]
        )

    x = run_async(func())
    assert x == 'x'

    async def func():
        # also works this way
        return varname(
            frame=2,
            ignore=[asyncio, (sys.modules[__name__],
                              'test_async_varname.<locals>.run_async')]
        )

    async def main():
        return await func()

    x = run_async(main())
    assert x == 'x'

def test_qualname_ignore_fail():
    # not a list
    def func():
        return varname(ignore=sys)

    with pytest.raises(AssertionError):
        f = func()

    # non-existing qualname
    def func():
        return varname(ignore=[(sys.modules[__name__], 'nosuchqualname')])

    with pytest.raises(AssertionError):
        f = func()

    # non-unique qualname
    def func():
        return varname(ignore=[(sys.modules[__name__],
                                'test_qualname_ignore_fail.<locals>.wrapper')])

    def wrapper():
        return func()

    wrapper2 = wrapper
    def wrapper():
        return func()

    with pytest.raises(AssertionError):
        f = func()
