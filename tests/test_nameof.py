import sys

import pytest
import subprocess
from varname import *

def test_nameof_pytest_fail():
    with pytest.raises(
        VarnameRetrievingError,
        match="Couldn't retrieve the call node. "
              "This may happen if you're using some other AST magic"
    ):
        assert nameof(nameof) == 'nameof'

def test_frame_fail_nameof(no_getframe):
    a = 1
    with pytest.raises(VarnameRetrievingError):
        nameof(a)

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
    name = nameof(a.b, vars_only=False)
    assert name == 'a.b'
    name = nameof(a.b.c)
    assert name == 'c'
    name = nameof(a.b.c, vars_only=False)
    assert name == 'a.b.c'

    d = [a, a]
    with pytest.raises(
            NonVariableArgumentError,
            match='is not a variable or an attribute'
    ):
        name = nameof(d[0], vars_only=True)

    # we are not able to retreive full names without source code available
    with pytest.raises(
            VarnameRetrievingError,
            match=('Are you trying to call nameof from exec/eval')
    ):
        eval('nameof(a.b, a)')


def test_nameof_from_stdin():
    code = ('from varname import nameof; '
            'x = lambda: 0; '
            'x.y = x; '
            'print(nameof(x.y, x))')
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
              'print(nameof(x.y, x))')
    code = compile(source, filename="<string2>", mode="exec")
    with pytest.raises(VarnameRetrievingError, match='Source code unavailable'):
        exec(code)

    source = ('from varname import nameof; '
              'x = lambda: 0; '
              'x.y = x; '
              'print(nameof(x.y, vars_only=True))')
    code = compile(source, filename="<string3>", mode="exec")
    with pytest.raises(
            VarnameRetrievingError,
            match="'nameof' can only be called with a single positional argument"):
        exec(code)

def test_nameof_wrapper():

    def decorator(f):
        def wrapper(var, *more_vars):
            name, more = f(var, more_vars, frame=2)
            return (name, *more)

        return wrapper

    wrap1 = decorator(nameof)
    x = y = 1
    name = wrap1(x, y)
    assert name == ('x', 'y')
