![varname][7]

[![Pypi][3]][4] [![Github][5]][6] [![PythonVers][8]][4] ![Building][10]
[![Docs and API][9]][15] [![Codacy][12]][13] [![Codacy coverage][14]][13]
[![Chat on gitter][17]][18]

Dark magics about variable names in python

[Change Log][16] | [API][15] | [Playground][11]

## Installation
```shell
pip install -U varname
```

## Features

- Core features:

  - Retrieving names of variables a function/class call is assigned to from inside it, using `varname`.
  - Retrieving variable names directly, using `nameof`
  - Detecting next immediate attribute name, using `will`

- Other helper APIs (built based on core features):

  - A value wrapper to store the variable name that a value is assigned to, using `Wrapper`
  - A decorator to register `__varname__` to functions/classes, using `register`
  - A `debug` function to print variables with their names and values

## Credits

Thanks goes to these awesome people/projects:

<table>
  <tr>
    <td align="center" style="min-width: 75px">
      <a href="https://github.com/alexmojaki">
        <img src="https://avatars0.githubusercontent.com/u/3627481?s=400&v=4" width="50px;" alt=""/>
        <br /><sub><b>@alexmojaki</b></sub>
      </a>
    </td>
    <td align="center" style="min-width: 75px">
      <a href="https://github.com/alexmojaki/executing">
        <img src="https://via.placeholder.com/50?text=executing" width="50px;" alt=""/>
        <br /><sub><b>executing</b></sub>
      </a>
    </td>
  </tr>
</table>

Special thanks to [@HanyuuLu][2] to give up the name `varname` in pypi for this project.

## Usage

### Retrieving the variable names using `varname(...)`

- From inside a function

    ```python
    from varname import varname
    def function():
        return varname()

    func = function()  # func == 'func'
    ```

    When there are intermediate frames:
    ```python
    def wrapped():
        return function()

    def function():
        # retrieve the variable name at the 2nd frame from this one
        return varname(frame=2)

    func = wrapped() # func == 'func'
    ```

    Or use `ignore` to ignore the wrapped frame:
    ```python
    def wrapped():
        return function()

    def function():
        return varname(ignore=wrapped)

    func = wrapped() # func == 'func'
    ```

    Calls from standard libraries are ignored by default:
    ```python
    import asyncio

    async def function():
        return varname()

    func = asyncio.run(function()) # func == 'func'
    ```

- Retrieving name of a class instance

    ```python
    class Foo:
        def __init__(self):
            self.id = varname()

        def copy(self):
            # also able to fetch inside a method call
            copied = Foo() # copied.id == 'copied'
            copied.id = varname() # assign id to whatever variable name
            return copied

    foo = Foo()   # foo.id == 'foo'

    foo2 = foo.copy() # foo2.id == 'foo2'
    ```

- Multiple variables on Left-hand side

    ```python
    # since v0.5.4
    def func():
        return varname(multi_vars=True)

    a = func() # a == ('a', )
    a, b = func() # (a, b) == ('a', 'b')
    [a, b] = func() # (a, b) == ('a', 'b')

    # hierarchy is also possible
    a, (b, c) = func() # (a, b, c) == ('a', 'b', 'c')
    ```

- Some unusual use

    ```python
    def function():
        return varname()

    func = [function()]    # func == ['func']

    func = [function(), function()] # func == ['func', 'func']

    func = function(), function()   # func = ('func', 'func')

    func = func1 = function()  # func == func1 == 'func'
    # a warning will be shown
    # since you may not want func1 to be 'func'

    x = func(y = func())  # x == 'x'

    # get part of the name
    func_abc = function()[-3:]  # func_abc == 'abc'

    # function alias supported now
    function2 = function
    func = function2()  # func == 'func'

    a = lambda: 0
    a.b = function() # a.b == 'b'

    # Since v0.1.3
    # We can ask varname to raise exceptions
    # if it fails to detect the variable name
    def get_name(raise_exc):
        return varname(raise_exc=raise_exc)

    a = {}
    a['b'] = get_name(True) # VarnameRetrievingError
    a['b'] = get_name(False) # None
    ```

### The decorator way to register `__varname__` to functions/classes

- Registering `__varname__` to functions

    ```python
    from varname.helpers import register

    @register
    def function():
        return __varname__

    func = function() # func == 'func'
    ```

    ```python
    # arguments also allowed (frame, ignore and raise_exc)
    @register(frame=2)
    def function():
        return __varname__

    def wrapped():
        return function()

    func = wrapped() # func == 'func'
    ```

- Registering `__varname__` as a class property

    ```python
    @register
    class Foo:
        ...

    foo = Foo()
    # foo.__varname__ == 'foo'
    ```

### Getting variable names directly using `nameof`

```python
from varname import varname, nameof

a = 1
nameof(a) # 'a'

b = 2
nameof(a, b) # ('a', 'b')

def func():
    return varname() + '_suffix'

f = func() # f == 'f_suffix'
nameof(f)  # 'f'

# get full names of (chained) attribute calls
func.a = func
nameof(func.a, full=True) # 'func.a'

func.a.b = 1
nameof(func.a.b, full=True) # 'func.a.b'
```

### Detecting next immediate attribute name
```python
from varname import will
class AwesomeClass:
    def __init__(self):
        self.will = None

    def permit(self):
        self.will = will(raise_exc=False)
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

### Value wrapper

```python
from varname.helpers import Wrapper

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

### Debugging with `debug`
```python
from varname.helpers import debug

a = 'value'
b = object()
debug(a) # DEBUG: a='value'
debug(b) # DEBUG: b=<object object at 0x2b70580e5f20>
debug(a, b)
# DEBUG: a='value'
# DEBUG: b=<object object at 0x2b70580e5f20>
debug(a, b, merge=True)
# DEBUG: a='value', b=<object object at 0x2b70580e5f20>
debug(a, repr=False, prefix='') # a=value
```

## Reliability and limitations
`varname` is all depending on `executing` package to look for the node.
The node `executing` detects is ensured to be the correct one (see [this][19]).

It partially works with environments where other AST magics apply, including
`pytest`, `ipython`, `macropy`, `birdseye`, `reticulate` with `R`, etc. Neither
`executing` nor `varname` is 100% working with those environments. Use
it at your own risk.

For example:

- This will not work with `pytest`:
  ```python
  a = 1
  assert nameof(a) == 'a'

  # do this instead
  name_a = nameof(a)
  assert name_a == 'a'
  ```

- `R` with `reticulate`.

[1]: https://github.com/pwwang/python-varname
[2]: https://github.com/HanyuuLu
[3]: https://img.shields.io/pypi/v/varname?style=flat-square
[4]: https://pypi.org/project/varname/
[5]: https://img.shields.io/github/tag/pwwang/python-varname?style=flat-square
[6]: https://github.com/pwwang/python-varname
[7]: logo.png
[8]: https://img.shields.io/pypi/pyversions/varname?style=flat-square
[9]: https://img.shields.io/github/workflow/status/pwwang/python-varname/Build%20Docs?label=docs&style=flat-square
[10]: https://img.shields.io/github/workflow/status/pwwang/python-varname/Build%20and%20Deploy?style=flat-square
[11]: https://mybinder.org/v2/gh/pwwang/python-varname/dev?filepath=playground%2Fplayground.ipynb
[12]: https://img.shields.io/codacy/grade/ed851ff47b194e3e9389b2a44d6f21da?style=flat-square
[13]: https://app.codacy.com/manual/pwwang/python-varname/dashboard
[14]: https://img.shields.io/codacy/coverage/ed851ff47b194e3e9389b2a44d6f21da?style=flat-square
[15]: https://pwwang.github.io/python-varname/api/varname
[16]: https://pwwang.github.io/python-varname/CHANGELOG/
[17]: https://img.shields.io/gitter/room/pwwang/python-varname?style=flat-square
[18]: https://gitter.im/python-varname/community
[19]: https://github.com/alexmojaki/executing#is-it-reliable
