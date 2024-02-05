import pytest
from varname import will, VarnameRetrievingError, ImproperUseError


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
    assert func.will == "abc"
    assert getattr(func, "will") == "abc"


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
    assert func.will == "abc"


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
            return "I will do something"

    c = C()
    x = c.iwill  # noqa F841
    assert c.will is None

    result = c.iwill.do()
    assert c.will == "do"
    assert result == "I will do something"


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
                raise AttributeError("Should do something with AwesomeClass object")

            # let self handle do
            return self

        def do(self):
            if self.wills[-1] != "do":
                raise AttributeError("You don't have permission to do")
            return "I am doing!"

        __getitem__ = permit

    awesome = AwesomeClass()
    with pytest.raises(AttributeError) as exc:
        awesome.do()
    assert str(exc.value) == "You don't have permission to do"

    with pytest.raises(AttributeError) as exc:
        awesome.permit()
    assert str(exc.value) == "Should do something with AwesomeClass object"

    # clear wills
    awesome = AwesomeClass()
    ret = awesome.permit().do()
    assert ret == "I am doing!"
    assert awesome.wills == [None, "do"]

    awesome = AwesomeClass()
    ret = awesome.myself().permit().do()
    assert ret == "I am doing!"
    assert awesome.wills == [None, "do"]

    awesome = AwesomeClass()
    ret = awesome().permit().do()
    assert ret == "I am doing!"
    assert awesome.wills == [None, "do"]

    awesome = AwesomeClass()
    ret = awesome.attr.permit().do()
    assert ret == "I am doing!"
    assert awesome.wills == [None, "do"]

    awesome = AwesomeClass()
    ret = awesome.permit().permit().do()
    assert ret == "I am doing!"
    assert awesome.wills == [None, "permit", "do"]

    with pytest.raises(AttributeError) as exc:
        print(awesome[2])
    assert str(exc.value) == "Should do something with AwesomeClass object"

    ret = awesome[2].do()
    assert ret == "I am doing!"


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
    assert x == "x"

    x = Foo().get_will_decor().x
    assert x == "x"


def test_will_fail():

    def get_will():
        return will()

    with pytest.raises(ImproperUseError):
        get_will()


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
