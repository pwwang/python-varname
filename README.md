# python-varname

[![Pypi][3]][4] [![Github][5]][6] [![PythonVers][8]][4] [![Travis building][10]][11] [![Codacy][12]][13] [![Codacy coverage][14]][13]

Dark magics about variable names in python

## Installation
```shell
pip install python-varname
```

## Features

- Fetching variable names from inside the function/class call
- Fetching variable names directly (added in `v0.1.2`)
- A value wrapper to store the value name that a value is assigned to (added in `v0.1.1`)
- Detecting next immediate attribute name (added in `v0.1.4`)
- Shortcut for `collections.namedtuple` (added in `v0.1.6`)

## Usage

### Retrieving the variable names from inside a function call/class instantiation

- From insdie a function call
    ```python
    from varname import varname
    def function():
        return varname()

    func = function()
    # func == 'func'
    ```

-  `varname` calls being buried deeply
    ```python
    def function():
        # I know that at which stack this will be called
        return varname(caller=3)

    def function1():
        return function()

    def function2():
        return function1()

    func = function2()
    # func == 'func'
    ```

- Retrieving instance name of a class
    ```python
    class Klass:
        def __init__(self):
            self.id = varname()

        def copy(self):
            # also able to fetch inside a member call
            return varname()

    k = Klass()
    # k.id == 'k'

    k2 = k.copy()
    # k2 == 'k2'
    ```

- Some unusual use
    ```python
    func = [function()]
    # func == ['func']

    func = [function(), function()]
    # func == ['func', 'func']

    func = function(), function()
    # func = ('func', 'func')

    func = func1 = function()
    # func == func1 == 'func'
    # a warning will be printed
    # since you may not want func1 to be 'func'

    x = func(y = func())
    # x == 'x'

    # get part of the name
    func_abc = function()[-3:]
    # func_abc == 'abc'

    # function alias supported now
    function2 = function
    func = function2()
    # func == 'func'

    # Since v0.1.3
    # We can ask varname to raise exceptions
    # if it fails to detect the variable name

    from varname import VarnameRetrievingError
    def get_name():
        try:
            # if raise_exc is False
            # "var_<index>" will be returned
            return varname(raise_exc=True)
        except VarnameRetrieveingError:
            return None

    a.b = get_name() # None
    ```

### Value wrapper

```python
from varname import Wrapper

foo = Wrapper(True)
# foo.name == 'foo'
# foo.value == True
bar = Wrapper(False)
# bar.name == 'bar'
# bar.value == False

def values_to_dict(*args):
    return {val.name: val.value for val in args}

mydict = values_to_dict(foo, bar)
# {'foo': True, 'bar': False}
```

### Getting variable names directly

```python
from varname import varname, nameof

a = 1
aname = nameof(a)
# aname == 'a

b = 2
aname, bname = nameof(a, b)
# aname == 'a', bname == 'b'

def func():
    return varname() + '_suffix'

f = func()
# f == 'f_suffix'
fname = nameof(f)
# fname == 'f'
```

### Detecting next immediate attribute name
```python
from varname import will
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
awesome.do() # AttributeError: You don't have permission to do
awesome.permit() # AttributeError: Should do something with AwesomeClass object
awesome.permit().do() == 'I am doing!'
```

### Shortcut for `collections.namedtuple`
```python
# instead of
from collections import namedtuple
Name = namedtuple('Name', ['first', 'last'])

# we can do:
from varname import namedtuple
Name = namedtuple(['first', 'last'])
```

## Limitations
- Working in `ipython REPL` but not in standard `python console`
- You have to know at which stack the function/class will be called
- For performance, since inspection is involved, better cache the name
- `nameof` cannot be used in statements in `pytest`
  ```
  a = 1
  assert nameof(a) == 'a'
  # Retrieving failure.
  # The right way:
  aname = nameof(a)
  assert aname == 'a'
  ```

[1]: https://github.com/pwwang/python-varname
[3]: https://img.shields.io/pypi/v/python-varname?style=flat-square
[4]: https://pypi.org/project/python-varname/
[5]: https://img.shields.io/github/tag/pwwang/python-varname?style=flat-square
[6]: https://github.com/pwwang/python-varname
[8]: https://img.shields.io/pypi/pyversions/python-varname?style=flat-square
[10]: https://img.shields.io/travis/pwwang/python-varname?style=flat-square
[11]: https://travis-ci.org/pwwang/python-varname
[12]: https://img.shields.io/codacy/grade/ed851ff47b194e3e9389b2a44d6f21da?style=flat-square
[13]: https://app.codacy.com/manual/pwwang/python-varname/dashboard
[14]: https://img.shields.io/codacy/coverage/ed851ff47b194e3e9389b2a44d6f21da?style=flat-square
