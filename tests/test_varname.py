import sys
import unittest

import pytest
from varname import (varname,
                     VarnameRetrievingWarning,
                     MultipleTargetAssignmentWarning,
                     VarnameRetrievingError,
                     Wrapper,
                     will,
                     inject,
                     namedtuple,
                     _get_node,
                     _bytecode_nameof,
                     nameof as original_nameof)

import varname as varname_module


def nameof(*args):
    """Test both implementations at the same time"""
    result = original_nameof(*args, caller=2)
    if len(args) == 1:
        assert result == _bytecode_nameof(caller=2)
    return result


varname_module.nameof = nameof


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


def test_function():

    def function():
        return varname()

    func = function()
    assert func == 'func'

    func = function(
    )
    assert func == 'func'

    func = \
        function()
    assert func == 'func'

    func = function \
        ()
    assert func == 'func'

    func = (function
            ())
    assert func == 'func'

    func = [function()]
    assert func == ['func']

    func = [function(), function()]
    assert func == ['func', 'func']

    func = (function(), )
    assert func == ('func', )

    func = (function(), function())
    assert func == ('func', 'func')

def test_function_context():

    def function(*args):
        return varname()

    func = function(
        1, # I
        2, # have
        3, # a
        4, # long
        5, # argument
        6, # list
    )
    assert func == 'func'

    def function(*args):
        return varname()

    func = function(
        1, # I
        2, # have
        3, # a
        4, # long
        5, # argument
        6, # list
    )
    assert func == 'func'

def test_function_deep():

    def function():
        # I know that at which stack this will be called
        return varname(caller = 3)

    def function1():
        return function()

    def function2():
        return function1()

    func = function2()
    assert func == 'func'

def test_class():

    class Klass:
        def __init__(self):
            self.id = varname()
        def copy(self):
            return varname()

    k = Klass()
    assert k.id == 'k'

    k2 = k.copy()
    assert k2 == 'k2'

def test_class_deep():

    class Klass:
        def __init__(self):
            self.id = self.some_internal()

        def some_internal(self):
            return varname(caller = 2)

        def copy(self):
            return self.copy_id()

        def copy_id(self):
            return self.copy_id_internal()

        def copy_id_internal(self):
            return varname(caller = 3)

    k = Klass()
    assert k.id == 'k'

    k2 = k.copy()
    assert k2 == 'k2'

def test_false():

    def func(**kwargs):
        return varname()

    x = func(
        y = func()
    )
    assert x == 'x'

    def func(**kwargs):
        return varname()

    x = func(y = func())
    assert x == 'x'

def test_referring():

    def Proc(**kwargs):
        return varname()

    def func2():
        pProc1 = Proc(
            input = {'infile:file': ['infile']},
            output = 'outfile:file:{{i.infile|__import__("pathlib").Path|.stem}}.txt',
            script = """cat {{i.infile}} > {{o.outfile}}""")
        pProc2 = Proc(
            input = 'infile:file',
            output = 'outfile:file:{{i.infile|__import__("pathlib").Path|.stem}}.txt',
            script = """echo world >> {{o.outfile}}""",
            depends = pProc1)
        return pProc1, pProc2

    assert func2() == ('pProc1', 'pProc2')

def test_only_one():

    def function():
        return varname()

    with pytest.raises(VarnameRetrievingError):
        x, y = function()
    with pytest.raises(VarnameRetrievingError):
        x, y = function(), function()
    with pytest.raises(VarnameRetrievingError):
        [x] = function()

def test_raise():

    def get_name():
        return varname(raise_exc=True)

    with pytest.raises(VarnameRetrievingError):
        get_name()

def test_multiple_targets():

    def function():
        return varname()

    with pytest.warns(MultipleTargetAssignmentWarning):
        y = x = function()
    assert y == x == 'y'

def test_unusual():

    def function():
        return varname()

    # something ridiculous
    xyz = function()[-1:]
    assert xyz == 'z'

    x = 'a'
    with pytest.warns(VarnameRetrievingWarning):
        x += function()
    assert x == 'avar_0'

    func = function
    x = func()
    assert x == 'x'

def test_wrapper():

    val1 = Wrapper(True)
    assert val1.name == 'val1'
    assert val1.value is True

    assert str(val1) == 'True'
    assert repr(val1) == "<Wrapper (name='val1', value=True)>"


class TestNameof(unittest.TestCase):
    def test_original_nameof(self):
        x = 1
        self.assertEqual(original_nameof(x), 'x')
        self.assertEqual(nameof(x), 'x')
        self.assertEqual(_bytecode_nameof(x), 'x')

    def test_nameof(self):
        a = 1
        b = nameof(a)
        assert b == 'a'
        nameof2 = nameof
        c = nameof2(a, b)
        assert b == 'a'
        assert c == ('a', 'b')

        def func():
            return varname() + 'abc'

        f = func()
        assert f == 'fabc'

        self.assertEqual(nameof(f), 'f')
        self.assertEqual('f', nameof(f))
        self.assertEqual(len(nameof(f)), 1)

        fname1 = fname = nameof(f)
        self.assertEqual(fname, 'f')
        self.assertEqual(fname1, 'f')

        with pytest.raises(VarnameRetrievingError):
            nameof(a==1)

        with pytest.raises(VarnameRetrievingError):
            _bytecode_nameof(a == 1)

        with pytest.raises(VarnameRetrievingError):
            nameof()

    def test_nameof_statements(self):
        a = {'test': 1}
        test = {}
        del a[nameof(test)]
        assert a == {}

        def func():
            return nameof(test)

        assert func() == 'test'

        def func2():
            yield nameof(test)

        assert list(func2()) == ['test']

        def func3():
            raise ValueError(nameof(test))

        with pytest.raises(ValueError) as verr:
            func3()
        assert str(verr.value) == 'test'

        for i in [0]:
            self.assertEqual(nameof(test), 'test')
            self.assertEqual(len(nameof(test)), 4)

    def test_nameof_expr(self):
        test = {}
        self.assertEqual(len(varname_module.nameof(test)), 4)

        lam = lambda: 0
        lam.a = 1
        self.assertEqual(
            varname_module.nameof(test, lam.a),
            ("test", "a"),
        )


def test_nameof_pytest_fail():
    with pytest.raises(
        VarnameRetrievingError,
        match="Couldn't retrieve the call node. "
              "This may happen if you're using some other AST magic"
    ):
        assert nameof(nameof) == 'nameof'


def test_bytecode_pytest_nameof_fail():
    with pytest.raises(
        VarnameRetrievingError,
        match="Found the variable name '@py_assert2' which is obviously wrong.",
    ):
        lam = lambda: 0
        lam.a = 1
        assert _bytecode_nameof(lam.a) == 'a'


def test_class_property():
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

# issue #18
def test_will_method():
    class AwesomeClass:
        def __init__(self):
            self.will = None

        def permit(self):
            self.will = will()
            if self.will == 'do':
                # let self handle do
                return self
            raise AttributeError('Should do something with AwesomeClass object')

        def do(self):
            if self.will != 'do':
                raise AttributeError("You don't have permission to do")
            return 'I am doing!'

    awesome = AwesomeClass()
    with pytest.raises(AttributeError) as exc:
        awesome.do()
    assert str(exc.value) == "You don't have permission to do"

    with pytest.raises(AttributeError) as exc:
        awesome.permit()
    assert str(exc.value) == 'Should do something with AwesomeClass object'

    ret = awesome.permit().do()
    assert ret == 'I am doing!'

def test_will_malformat():
    """Function will has to be used in the format of `inst.attr` or
    `inst.attr()`"""
    class C1:
        def __getitem__(self, name):
            return will(raise_exc=True)

    class C2:
        def __getitem__(self, name):
            return will(raise_exc=False)

    c1 = C1()
    with pytest.raises(VarnameRetrievingError):
        c1[1]

    c2_will = C2()[1]
    assert c2_will is None


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

    with pytest.warns(VarnameRetrievingWarning):
        b = func(False)
    assert b.startswith('var_')


def test_frame_fail_nameof(no_getframe):
    a = 1
    with pytest.raises(VarnameRetrievingError):
        assert nameof(a) == 'a'


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

def test_namedtuple():
    Name = namedtuple(['first', 'last'])
    name = Name('Bill', 'Gates')
    assert isinstance(name, Name)

def test_inject():

    with pytest.raises(VarnameRetrievingError):
        a = inject(1)

    class A(list):
        pass

    a = inject(A())
    b = inject(A())
    assert a.__varname__ == 'a'
    assert b.__varname__ == 'b'
    assert a == b
    a.append(1)
    b.append(1)
    assert a == b


def test_no_source_code_nameof():
    assert eval('nameof(list)') == eval('original_nameof(list)') == 'list'

    with pytest.raises(VarnameRetrievingError):
        eval("original_nameof(list, list)")


class Weird:
    def __add__(self, other):
        _bytecode_nameof(caller=2)


def test_bytecode_nameof_wrong_node():
    with pytest.raises(
        VarnameRetrievingError,
        match='Did you call nameof in a weird way',
    ):
        Weird() + Weird()
