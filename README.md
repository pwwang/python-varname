# python-varname

[![Pypi][3]][4] [![Github][5]][6] [![PythonVers][8]][4] [![Travis building][10]][11] [![Codacy][12]][13] [![Codacy coverage][14]][13]

Dark magics about variable names in python

## Installation
```shell
pip install python-varname
```

## Usage

### Retrieving the variable name inside a function

```python
from varname import varname
def function():
    return varname()

func = function()
# func == 'func'

# available calls to retrieve
func = function(
    # ...
)

func = \
    function()

func = function \
    ()

func = (function
        ())
```


### `varname` calls being buried deeply
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

### Retrieving instance name of a class object
```python
class Klass:
    def __init__(self):
        self.id = varname()
    def copy(self):
        return varname()

k = Klass()
# k.id == 'k'

k2 = k.copy()
# k2 == 'k2'
```

### `varname` calls being buried deeply for classes
```python
class Klass:
    def __init__(self):
        self.id = self.some_internal()

    def some_internal(self):
        return varname(caller=2)

    def copy(self):
        return self.copy_id()

    def copy_id(self):
        return self.copy_id_internal()

    def copy_id_internal(self):
        return varname(caller=3)

k = Klass()
# k.id == 'k'

k2 = k.copy()
# k2 == 'k2'
```

## Some unusual use

```python
func = [function()]
# func == ['func']

func = [function(), function()]
# func == ['func', 'func']

func = function(), function()
# func = ('func', 'func')

func = func1 = function()
# func == func1 == 'func1'
# a warning will be printed

x = func(
    y = func()
)
# x == 'x'

# get part of the name
func_abc = function()[-3:]
# func_abc == 'abc'

# function alias supported now
function2 = function
func = function2()
# func == 'func'
```

## A value wrapper (added in v0.1.1)

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

## Getting variable names directly (added in v0.2.0)

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

## Limitations
- Working in `ipython REPL` but not in standard `python console`
- You have to know at which stack the function/class will be called
- For performance, since inspection is involved, better cache the name
- `nameof` cannot be used in statements
  ```
  a = 1
  assert nameof(a) == 'a'
  # IncorrectUseOfNameof: Should not use nameof it in statements.
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
