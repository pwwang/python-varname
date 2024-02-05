import sys
import subprocess
from functools import wraps

import pytest
from executing import Source
from varname import varname
from varname.utils import (
    VarnameRetrievingError,
    QualnameNonUniqueError,
    ImproperUseError,
    MaybeDecoratedFunctionWarning,
    MultiTargetAssignmentWarning,
    get_node,
)


from .conftest import run_async, module_from_source

SELF = sys.modules[__name__]


def test_function():

    def function():
        return varname()

    func = function()
    assert func == "func"


def test_function_with_frame_arg():

    def function():
        # I know that at which frame (3rd) this will be called
        return varname(frame=3)

    def function1():
        return function()

    def function2():
        return function1()

    func = function2()
    assert func == "func"


def test_class():

    class Foo:
        def __init__(self):
            self.id = varname()

        def copy(self):
            return varname()

    k = Foo()
    assert k.id == "k"

    k2 = k.copy()
    assert k2 == "k2"


def test_class_with_frame_arg():

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
    assert k.id == "k"

    k2 = k.copy()
    assert k2 == "k2"


def test_single_var_lhs_required():
    """Only one variable to receive the name on LHS"""

    def function():
        return varname()

    with pytest.raises(
        ImproperUseError, match="Expect a single variable on left-hand side"
    ):
        x, y = function()

    with pytest.raises(ImproperUseError):
        x, y = function(), function()  # noqa: F841


def test_multi_vars_lhs():
    """Tests multiple variables on the left hand side"""

    def function():
        return varname(multi_vars=True)

    a, b = function()
    assert (a, b) == ("a", "b")
    [a, b] = function()
    assert (a, b) == ("a", "b")
    a = function()
    assert a == ("a",)
    # hierarchy
    a, (b, c) = function()
    assert (a, b, c) == ("a", "b", "c")
    # with attributes
    x = lambda: 1
    a, (b, x.c) = function()
    assert (a, b, x.c) == ("a", "b", "x.c")

    # Not all LHS are variables
    y = {}
    with pytest.raises(
        ImproperUseError,
        match=r"Node 'y\[BinOp\]' detected",
    ):
        y[1 + 1] = function()


def test_raise_exc():

    def get_name(raise_exc):
        return varname(raise_exc=raise_exc, strict=False)

    with pytest.raises(ImproperUseError):
        get_name(True)

    name = "0"
    # we can't get it in such way, even with strict=False
    with pytest.raises(ImproperUseError):
        name += str(get_name(False))


def test_strict():

    def foo(x):
        return x

    def function():
        return varname(strict=True)

    func = function()
    assert func == "func"

    with pytest.raises(ImproperUseError):
        func = function() + "_"

    with pytest.raises(ImproperUseError):
        func = foo(function())

    with pytest.raises(ImproperUseError):
        func = [function()]


def test_not_strict():

    def function():
        return varname(strict=False)

    func = function()
    assert func == "func"

    func = [function()]
    assert func == ["func"]

    func = [function(), function()]
    assert func == ["func", "func"]

    func = (function(),)
    assert func == ("func",)

    func = (function(), function())
    assert func == ("func", "func")


@pytest.mark.skipif(
    sys.version_info < (3, 8), reason="named expressions require Python >= 3.8"
)
def test_named_expr():
    from .named_expr import a

    assert a == ["b", "c"]


def test_multiple_targets():

    def function():
        return varname()

    with pytest.warns(
        MultiTargetAssignmentWarning, match="Multiple targets in assignment"
    ):
        y = x = function()
    assert y == x == "x"


def test_subscript():

    class C:
        def __init__(self):
            self.value = None

        def __setitem__(self, key, value):
            self.value = value

    x = {"a": 1, "b": 2}
    y = [0, 1, 2, 3, 4]
    a = "a"
    b = 1
    c = C()

    def func():
        return varname()

    x[0] = func()
    assert x[0] == "x[0]"
    x[a] = func()
    assert x[a] == "x[a]"
    x["a"] = func()
    assert x["a"] == "x['a']"
    c[[1]] = func()
    assert c.value == "c[[1]]"
    c[(1,)] = func()
    assert c.value == "c[(1,)]"
    c[(1, 2)] = func()
    assert c.value == "c[(1, 2)]"
    y[b] = func()
    assert y[b] == "y[b]"
    y[1] = func()
    assert y[1] == "y[1]"
    c[1:4:2] = func()
    assert c.value == "c[1:4:2]"
    c[1:4:2, 1:4:2] = func()
    assert c.value == "c[(1:4:2, 1:4:2)]"
    c[1:] = func()
    assert c.value == "c[1:]"
    c[:4] = func()
    assert c.value == "c[:4]"
    c[:] = func()
    assert c.value == "c[:]"


def test_unusual():

    def function():
        return varname(strict=False)

    # something ridiculous
    xyz = function()[-1:]
    assert xyz == "z"

    x = "a"
    with pytest.raises(ImproperUseError):
        x += function()
    assert x == "a"

    # alias
    func = function
    x = func()
    assert x == "x"


def test_from_property():
    class C:
        @property
        def var(self):
            return varname()

    c = C()
    v1 = c.var
    assert v1 == "v1"


def test_frame_fail(no_getframe):
    """Test when failed to retrieve the frame"""
    # Let's monkey-patch inspect.stack to do this
    assert get_node(1) is None

    def func(raise_exc):
        return varname(raise_exc=raise_exc)

    with pytest.raises(VarnameRetrievingError):
        a = func(True)  # noqa: F841

    b = func(False)
    assert b is None


def test_ignore_module_filename():
    source = "def foo(): return bar()"

    code = compile(source, "<string>", "exec")

    def bar():
        return varname(ignore="<string>")

    globs = {"bar": bar}
    exec(code, globs)
    foo = globs["foo"]
    f = foo()
    assert f == "f"


def test_ignore_module_no_file(tmp_path):
    module = module_from_source(
        "ignore_module",
        """
        def foo():
            return bar()
        """,
        tmp_path,
    )
    # force injecting __varname_ignore_id__
    del module.__file__

    def bar():
        return varname(
            ignore=[
                (module, "foo"),  # can't get module by inspect.getmodule
                module,
            ]
        )

    module.bar = bar

    f = module.foo()
    assert f == "f"


def test_ignore_module_qualname_no_source(tmp_path):
    module = module_from_source(
        "ignore_module_qualname_no_source",
        """
        def bar():
            return 1
        """,
        tmp_path,
    )
    source = Source.for_filename(module.__file__)
    # simulate when source is not available
    # no way to check uniqueness of qualname
    source.tree = None

    def foo():
        return varname(ignore=(module, "bar"))

    f = foo()  # noqa: F841


def test_ignore_module_qualname_ucheck_in_match(
    tmp_path, frame_matches_module_by_ignore_id_false
):
    module = module_from_source(
        "ignore_module_qualname_no_source_ucheck_in_match",
        """
        def foo():
            return bar()
        """,
        tmp_path,
    )
    # force uniqueness to be checked in match
    # module cannot be fetched by inspect.getmodule
    module.__file__ = None

    def bar():
        return varname(
            ignore=[
                (
                    module,
                    "foo",
                ),  # frame_matches_module_by_ignore_id_false makes this fail
                (None, "foo"),  # make sure foo to be ignored
            ]
        )

    module.bar = bar

    f = module.foo()
    assert f == "f"


def test_ignore_module_qualname(tmp_path, capsys, enable_debug):
    module = module_from_source(
        "ignore_module_qualname",
        """
        def foo1():
            return bar()
        """,
        tmp_path,
    )

    module.__file__ = None
    # module.__varname_ignore_id__ = object()

    def bar():
        var = varname(ignore=(module, "foo1"))
        return var

    module.bar = bar

    f = module.foo1()
    assert f == "f"


def test_ignore_filename_qualname():
    source = (
        "import sys\n"
        "import __main__\n"
        "import varname\n"
        "varname.config.debug = True\n"
        "from varname import varname\n"
        "def func(): \n"
        "  return varname(ignore=[\n"
        '     ("unknown", "wrapped"), \n'  # used to trigger filename mismatch
        '     ("<stdin>", "wrapped")\n'
        "  ])\n\n"
        "def wrapped():\n"
        "  return func()\n\n"
        "variable = wrapped()\n"
    )

    # code = compile(source, '<string>', 'exec')
    # # ??? NameError: name 'func' is not defined
    # exec(code)

    p = subprocess.Popen(
        [sys.executable],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf8",
    )
    out, _ = p.communicate(input=source)
    assert "Ignored by IgnoreFilenameQualname('<stdin>', 'wrapped')" in out


def test_ignore_function_warning():

    def my_decorator(f):
        @wraps(f)
        def wrapper():
            return f()

        return wrapper

    @my_decorator
    def func1():
        return func2()

    def func2():
        return varname(ignore=[func1, (func1, 1)])

    with pytest.warns(
        MaybeDecoratedFunctionWarning,
        match="You asked varname to ignore function 'func1'",
    ):
        f = func1()  # noqa: F841


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
    assert f4 == "f4"

    @my_decorator
    def foo6():
        return foo7()

    def foo7():
        return varname(ignore=(foo4, 100))

    with pytest.raises(ImproperUseError):
        f6 = foo6()  # noqa: F841


def test_ignore_dirname(tmp_path):
    module = module_from_source(
        "ignore_dirname",
        """
        from varname import varname
        def bar(dirname):
            return varname(ignore=[dirname])
        """,
        tmp_path,
    )

    def foo():
        return module.bar(tmp_path)

    f = foo()
    assert f == "f"


def test_type_anno_varname():

    class Foo:
        def __init__(self):
            self.id = varname()

    foo: Foo = Foo()
    assert foo.id == "foo"


def test_generic_type_varname():
    from typing import Generic, TypeVar

    T = TypeVar("T")

    class Foo(Generic[T]):
        def __init__(self):
            # Standard libraries are ignored by default now (0.6.0)
            # self.id = varname(ignore=[typing])
            self.id = varname()

    foo = Foo[int]()
    assert foo.id == "foo"

    bar: Foo = Foo[str]()
    assert bar.id == "bar"

    baz = Foo()
    assert baz.id == "baz"


def test_async_varname():
    from . import conftest

    async def func():
        return varname(ignore=(conftest, "run_async"))

    async def func2():
        return varname(ignore=run_async)

    x = run_async(func())
    assert x == "x"

    x2 = run_async(func2())
    assert x2 == "x2"

    # frame and ignore together
    async def func3():
        # also works this way
        return varname(frame=2, ignore=run_async)

    async def main():
        return await func3()

    x3 = run_async(main())
    assert x3 == "x3"


def test_invalid_ignores():
    # unexpected ignore item
    def func():
        return varname(ignore=1)

    with pytest.raises(ValueError):
        f = func()

    def func():
        return varname(ignore=(1, 2))

    with pytest.raises(ValueError):
        f = func()

    def func():
        return varname(ignore=(1, "2"))

    with pytest.raises(ValueError):
        f = func()  # noqa: F841


def test_qualname_ignore_fail():
    # non-unique qualname
    def func():
        return varname(
            ignore=[(SELF, "test_qualname_ignore_fail.<locals>.wrapper")]
        )

    def wrapper():
        return func()

    wrapper2 = wrapper  # noqa: F841

    def wrapper():
        return func()

    with pytest.raises(QualnameNonUniqueError):
        f = func()  # noqa: F841


def test_ignore_lambda():
    def foo():
        return varname()

    bar = lambda: foo()

    b = bar()
    assert b == "b"


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
                (SELF, "*.wrapper"),
                # unrelated qualname will not be hit at all
                (sys, "wrapper"),
            ],
        )

    x = foo1()
    assert x == "x"
    msgs = capsys.readouterr().err.splitlines()
    assert ">>> IgnoreList initiated <<<" in msgs[0]
    assert "Ignored by IgnoreModule('varname')" in msgs[1]
    assert "Skipping (2 more to skip) [In 'foo3'" in msgs[2]
    assert (
        "Ignored by IgnoreModuleQualname('tests.test_varname', '*.wrapper')"
        in msgs[3]
    )
    assert "Skipping (1 more to skip) [In 'foo2'" in msgs[4]
    assert (
        "Ignored by IgnoreModuleQualname('tests.test_varname', '*.wrapper')"
        in msgs[5]
    )
    assert "Skipping (0 more to skip) [In 'foo1'" in msgs[6]
    assert (
        "Ignored by IgnoreModuleQualname('tests.test_varname', '*.wrapper')"
        in msgs[7]
    )
    assert "Gotcha! [In 'test_internal_debug'" in msgs[8]


def test_star_var():
    def func():
        v = varname(multi_vars=True)
        return 1, 2, 3, v

    a, *b, c = func()
    assert a == 1
    assert b == [2, 3]
    assert c == ("a", "*b", "c")
