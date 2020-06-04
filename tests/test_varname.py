import pytest
from varname import (varname,
                     VarnameRetrievingWarning,
                     MultipleTargetAssignmentWarning,
                     VarnameRetrievingError,
                     Wrapper,
                     will,
                     nameof)

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

    with pytest.raises(VarnameRetrievingError):
        assert nameof(f)

    fname1 = fname = nameof(f)
    assert fname1 == fname == 'f'

    with pytest.raises(VarnameRetrievingError):
        nameof(a==1)

    with pytest.raises(VarnameRetrievingError):
        nameof()


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
