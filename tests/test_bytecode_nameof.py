import pytest
import unittest
from varname import _bytecode_nameof
from varname import nameof, varname, VarnameRetrievingError

def nameof_both(*args):
    """Test both implementations at the same time"""
    result = nameof(*args, frame=2)
    if len(args) == 1:
        assert result == _bytecode_nameof(frame=2)
    return result

class Weird:
    def __add__(self, other):
        _bytecode_nameof(frame=2)

class TestNameof(unittest.TestCase):
    def test_original_nameof(self):
        x = 1
        self.assertEqual(nameof(x), 'x')
        self.assertEqual(nameof_both(x), 'x')
        self.assertEqual(_bytecode_nameof(x), 'x')

    def test_bytecode_nameof_wrong_node(self):
        with pytest.raises(
                VarnameRetrievingError,
                match='Did you call nameof in a weird way',
        ):
            Weird() + Weird()

    def test_bytecode_pytest_nameof_fail(self):
        with pytest.raises(
                VarnameRetrievingError,
                match=("Found the variable name '@py_assert2' "
                       "which is obviously wrong."),
        ):
            lam = lambda: 0
            lam.a = 1
            assert _bytecode_nameof(lam.a) == 'a'

    def test_nameof(self):
        a = 1
        b = nameof_both(a)
        assert b == 'a'
        nameof2 = nameof_both
        c = nameof2(a, b)
        assert b == 'a'
        assert c == ('a', 'b')
        def func():
            return varname() + 'abc'

        f = func()
        assert f == 'fabc'

        self.assertEqual(nameof_both(f), 'f')
        self.assertEqual('f', nameof_both(f))
        self.assertEqual(len(nameof_both(f)), 1)

        fname1 = fname = nameof_both(f)
        self.assertEqual(fname, 'f')
        self.assertEqual(fname1, 'f')

        with pytest.raises(VarnameRetrievingError):
            nameof_both(a==1)

        with pytest.raises(VarnameRetrievingError):
            _bytecode_nameof(a == 1)

        # this is avoided by requiring the first argument `var`
        # with pytest.raises(VarnameRetrievingError):
        #     nameof_both()

    def test_nameof_statements(self):
        a = {'test': 1}
        test = {}
        del a[nameof_both(test)]
        assert a == {}

        def func():
            return nameof_both(test)

        assert func() == 'test'

        def func2():
            yield nameof_both(test)

        assert list(func2()) == ['test']

        def func3():
            raise ValueError(nameof_both(test))

        with pytest.raises(ValueError) as verr:
            func3()
        assert str(verr.value) == 'test'

        for i in [0]:
            self.assertEqual(nameof_both(test), 'test')
            self.assertEqual(len(nameof_both(test)), 4)

    def test_nameof_expr(self):
        lam = lambda: 0
        lam.a = 1
        lam.lam = lam
        lams = [lam]

        lam.nameof = nameof_both

        test = {}
        self.assertEqual(len(lam.nameof(test)), 4)

        self.assertEqual(
            lam.nameof(test, lam.a),
            ("test", "a"),
        )

        self.assertEqual(nameof_both(lam.a), "a")
        self.assertEqual(nameof_both(lam.lam.lam.lam.a), "a")
        self.assertEqual(nameof_both(lam.lam.lam.lam), "lam")
        self.assertEqual(nameof_both(lams[0].lam), "lam")
        self.assertEqual(nameof_both(lams[0].lam.a), "a")
        self.assertEqual(nameof_both((lam() or lams[0]).lam.a), "a")