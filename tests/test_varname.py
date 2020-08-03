import sys
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


def test_original_nameof():
    x = 1
    assert original_nameof(x) == nameof(x) == _bytecode_nameof(x) == 'x'



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

def test_nameof():
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

    assert nameof(f) == 'f'
    assert 'f' == nameof(f)
    assert len(nameof(f)) == 1

    fname1 = fname = nameof(f)
    assert fname1 == fname == 'f'

    with pytest.raises(VarnameRetrievingError):
        nameof(a==1)

    with pytest.raises(VarnameRetrievingError):
        nameof()

def test_nameof_statements():
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
        assert nameof(test) == 'test'
        assert len(nameof(test)) == 4

def test_nameof_expr():
    test = {}
    assert len(varname_module.nameof(test)) == 4

    lam = lambda: 0
    lam.a = 1
    with pytest.raises(VarnameRetrievingError) as vrerr:
        varname_module.nameof(test, lam.a)
    assert str(vrerr.value) == ("Only variables should "
                                "be passed to nameof.")

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

def test_will_property():

    class C:
        def __init__(self):
            self.will = None

        @property
        def iwill(self):
            self.will = will()
            return self

        def do(self):
            return 'I will do something'

    c = C()
    assert c.iwill.do() == 'I will do something'

def test_will_fail():

    def get_will():
        return {'a': will(raise_exc=True)}

    with pytest.raises(VarnameRetrievingError):
        get_will()['a']


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
    with pytest.raises(ValueError):
        assert nameof(a) == 'a'
        raise ValueError



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
