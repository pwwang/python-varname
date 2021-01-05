import sys

import pytest
import subprocess
from varname import *
from varname.helpers import *
from varname.utils import get_node

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
    _varname.config.debug = True
    yield
    _varname.config.debug = False

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
                       match='Expect a single variable on left-hand side'):
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

def test_varname_from_attributes():
    class C:
        @property
        def var(self):
            return varname()

    c = C()
    v1 = c.var
    assert v1 == 'v1'

def test_frame_fail(no_getframe):
    """Test when failed to retrieve the frame"""
    # Let's monkey-patch inspect.stack to do this
    assert get_node(1) is None


def test_frame_fail_varname(no_getframe):
    def func(raise_exc):
        return varname(raise_exc=raise_exc)

    with pytest.raises(VarnameRetrievingError):
        a = func(True)

    b = func(False)
    assert b is None

def test_ignore_module_filename():
    source = ('def foo(): return bar()')

    code = compile(source, '<string>', 'exec')
    def bar():
        return varname(ignore='<string>')

    globs = {'bar': bar}
    exec(code, globs)
    foo = globs['foo']
    f = foo()
    assert f == 'f'

def test_ignore_module_no_file(tmp_path):
    modfile = tmp_path / 'ignore_module8525.py'
    modfile.write_text("def foo(): return bar()")
    sys.path.insert(0, str(tmp_path))
    modu = __import__('ignore_module8525')
    # force injecting __varname_ignore_id__
    del modu.__file__

    def bar():
        return varname(ignore=[
            (modu, 'foo'), # can't get module by inspect.getmodule
            modu
        ])
    modu.bar = bar

    f = modu.foo()
    assert f == 'f'


def test_ignore_module_filename_qualname():
    source = ('import sys\n'
              'import __main__\n'
              'import varname\n'
              'varname.config.debug = True\n'
              'from varname import varname\n'
              'def func(): \n'
              '  return varname(ignore=[("<stdin>", "wrapped")])\n\n'
              'def wrapped():\n'
              '  return func()\n\n'
              'variable = wrapped()\n')

    # code = compile(source, '<string>', 'exec')
    # # ??? NameError: name 'func' is not defined
    # exec(code)

    p = subprocess.Popen([sys.executable],
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         encoding='utf8')
    out, _ = p.communicate(input=source)
    assert "Ignored by <IgnoreQualname('<stdin>', wrapped)>" in out

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
            ignore=[
                (
                    sys.modules[__name__],
                    "test_internal_debug.<locals>.my_decorator.<locals>.wrapper"
                ),
                # unrelated qualname will not hit at all
                (sys, 'wrapper')
            ]
        )

    x = foo1()
    assert x == 'x'
    msgs = capsys.readouterr().err.splitlines()
    assert "Ignored by <IgnoreModule('varname')>" in msgs[0]
    assert "Skipping (2 more to skip) [In 'foo3'" in msgs[1]
    assert "Ignored by <IgnoreQualname('tests.test_varname', test_internal_debug.<locals>.my_decorator.<locals>.wrapper)>" in msgs[2]
    assert "Skipping (1 more to skip) [In 'foo2'" in msgs[3]
    assert "Ignored by <IgnoreQualname('tests.test_varname', test_internal_debug.<locals>.my_decorator.<locals>.wrapper)>" in msgs[4]
    assert "Skipping (0 more to skip) [In 'foo1'" in msgs[5]
    assert "Ignored by <IgnoreQualname('tests.test_varname', test_internal_debug.<locals>.my_decorator.<locals>.wrapper)>" in msgs[6]
    assert "Gotcha! [In 'test_internal_debug'" in msgs[7]

def test_ignore_decorated():
    def my_decorator(f):
        def wrapper():
            return f()
        return wrapper

    @my_decorator
    def foo4():
        return foo5()

    def foo5():
        return varname(ignore=(foo4, 1))

    f4 = foo4()
    assert f4 == 'f4'

    @my_decorator
    def foo6():
        return foo7()

    def foo7():
        return varname(ignore=(foo4, 100))

    with pytest.raises(VarnameRetrievingError):
        f6 = foo6()

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
    async def func2():
        return varname(ignore=[asyncio, run_async])

    x = run_async(func())
    assert x == 'x'

    x2 = run_async(func2())
    assert x2 == 'x2'

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
    # unexpected ignore item
    def func():
        return varname(ignore=1)
    with pytest.raises(ValueError):
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

def test_ignore_lambda():
    def foo():
        return varname()

    bar = lambda: foo()

    b = bar()
    assert b == 'b'

def test_ignore_comprehensions(enable_debug):

    def foo():
        return varname()

    bar = [lambda: foo() for i in [0]]
    b = bar[0]()
    assert b == 'b'
