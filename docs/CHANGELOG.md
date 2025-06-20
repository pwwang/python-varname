# Change Log

## 0.15.0

- revert: bring nameof back (#117)

## 0.14.0

- BREAKING CHANGE: deprecate nameof (see https://github.com/pwwang/python-varname/issues/117#issuecomment-2558358294)
- docs: remove deprecated nameof examples from README
- chore(deps): update asttokens to version 3.0.0 and adjust dependencies
- style: clean up unused imports and add spacing for readability for test files
- ci: update build workflow to use Ubuntu 24.04 and adjust Python version conditions
- chore(deps): add ipykernel dev dependency version 6.29.5 to run playground notebook
- chore(deps): update content-hash in poetry.lock after dependency changes

## 0.13.5

- deps: bump up executing to ^2.1 to fix issues with python3.13

## 0.13.4

- core: switch to poetry-core (#113)
- deps: bump up dependencies
- feat: support python 3.13 (#116)
- ci: use latest CI actions
- DEPRECATED: add warning to deprecate nameof in the future

## 0.13.3

- feat: support frame to allow wrapping for `helpers.jsobj()` (#111)

## 0.13.2

- deps: bump up pytest to v8
- feat: support vars_only to keep parents of an attribute for `helpers.jsobj()` (#110)

## 0.13.1

- style: create py.typed for mypy compatibility (#109)

## 0.13.0

- style: change max line length to 88
- style: clean up test code styles
- feat: support subscript node for varname (#104)
- ci: remove python3.8 from CI
- breaking!: `varname` of `a.b` now returns `"a.b"` instead of `"a"`

## 0.12.2

- Add `helpers.exec_code` function to replace `exec` so that source code available at runtime

## 0.12.1

- Bump executing to 2.0.1

## v0.12.0

- Support python 3.12
- Update python3.12 to CI
- Bump executing to ^2.0
- Bump up other dependencies
- Add Dockerfile for codesandbox

## v0.11.2

- ✨ Add `jsobj` to create dict without explicitly specifying the key-value pairs

    ```python
    from varname.helpers import jsobj

    a = 1
    b = 2
    # before
    dict(a=a, b=b, c=3)  # {'a': 1, 'b': 2, 'c': 3}

    # after
    jsobj(a, b, c=3)  # {'a': 1, 'b': 2, 'c': 3}
    ```

## v0.11.1

- ✨ Support starred variable for varname() (#96)
- ✅ Fix tests
- 📝 Update docs for `varname(strict=...)`

## v0.11.0

- 📝 Update README for shields badges (#91)
- 🏷️ Overload types for nameof and argname (#77)
- 💥 Drop python <3.8  for v0.11
     If you need support for python <3.8, please use varname <0.11

## v0.10.0

- ✨ Support python 3.11

## v0.9.1

- ⬆️ Upgrade executing to 1.0

## v0.9.0

- ⬆️ Upgrade executing to 0.9
- 🗑️ Remove deprecated `argname2`
- ✨ Support constants for `argname` even when `vars_only=True`
- ✨ Support `__getattr__/__setattr__` etc for `argname`

    Now you can do:

    ```python
    from varname import argname

    class Foo:
        def __getattr__(self, name):
            """Similar for `__getitem__`"""
            print(argname("name"))

        def __setattr__(self, name, value):
            """Similar for `__setitem__`"""
            print(argname("name"))
            print(argname("value"))

        def __add__(self, other):
            """Similar for `__sub__`, `__mul__`, `__truediv__`, `__floordiv__`,
            `__mod__`, `__pow__`, `__lshift__`, `__rshift__`, `__matmul__`,
            `__and__`, `__xor__`, `__or__`
            """
            print(argname("other"))

        def __eq__(self, other):
            """Similar for `__lt__`, `__le__`, `__gt__`, `__ge__`, `__ne__`
            """
            print(argname("other"))

    foo = Foo()
    b = 1
    foo.x  # prints: 'x' (note the quotes)
    foo.x = b  # prints: 'x' and b
    foo + b  # prints: b
    foo == b  # prints: b
    ```

## v0.8.3

This is more of a housekeeping release:

- ⬆️ Upgrade `executing` to 0.8.3 to make varname work with ipython 8+
- 📝 Update `README.md` to add new contributors
- 🚨 Use `flake8` instead of `pylint` for linting

## v0.8.2

### Fixes

- 🩹 Use sysconfig instead of distutils.sysconfig to avoid deprecatewarning for python 3.10+

### Housekeeping

- 👷 Add python3.10 in CI
- 📄 Add license back

## v0.8.1

- Handle inspect raises "could not get source code" when printing rich exception message

## v0.8.0

Compared to `v0.7.3`

- Add `UsingExecWarning` when `exec` is used to retrieve `func` for `argname()`.
- Remove `NonVariableArgumentError`. Use `ImproperUseError` instead.
- Add `VarnameError` and `VarnameWarning` as root for varname-related exceptions and warnings, respectively.
- Default `strict` to `True` for `varname()`, `helpers.register()` and `helpers.Wrapper()`
- Limit number of context lines for showing where `ImproperUseError` happens

Compared to `v0.7.0`

- Add `UsingExecWarning` when `exec` is used to retrieve `func` for `argname()`.
- Remove `NonVariableArgumentError`. Use `ImproperUseError` instead.
- Add `VarnameError` and `VarnameWarning` as root for varname-related exceptions and warnings, respectively.
- Add `strict` mode to `varname()`, `helpers.register()` and `helpers.Wrapper()` (#57)
- Support the walrus operator (`:=`) (#58)
- Change `argname()` to accept argument names instead of arguments themselves
- Remove `pos_only` argument from `argname()`
- Add `ignore` argument to `argname()` to ignore intermediate frames
- Limit `VarnameRetrievingError` to the situations only when the AST node is not able to be retrieved.

## v0.7.3

- Indicate where the `ImproperUseError` happens for `varname()` (Close #60)
- Add `VarnameException` and `VarnameWarning` as root for all varname-defined exceptions and warnings.

## v0.7.2

- Add `strict` mode to `varname()` (#57)
- Support the walrus operator (`:=`) (#58)

## v0.7.1

- Add `ignore` argument to `argname2()`
- Fix Fix utils.get_argument_sources() when kwargs is given as `**kwargs`.

## v0.7.0

- `ImproperUseError` is now independent of `VarnameRetrievingError`
- Deprecate `argname`, superseded by `argname2`

  ```python
    >>> argname(a, b, ...) # before
    >>> argname2('a', 'b', ...) # after
  ```

- Add `dispatch` argument to `argname`/`argment2` to be used for single-dispatched functions.

## v0.6.5

- Add `sep` argument to `helpers.debug()`

## v0.6.4

- Add ImproperUseError to distinguish node retrieving error from improper varname use #49

## v0.6.3

- Fix standard library ignoring ignores 3rd-party libraries under site-packages/
- Allow pathlib.Path object to be used in ignore items

## v0.6.2

- Remove argument `full` for `nameof`, use `vars_only` instead. When `vars_only=False`, source of the argument returned.

  ```python
  # before:
  nameof(a.b, full=True) # 'a.b'
  nameof(x[0], full=True) # unable to fetch
  # after (requires asttoken):
  nameof(a.b, vars_only=False) # 'a.b'
  nameof(x[0], vars_only=False) # 'x[0]'
  ```

- Add argument `frame` to `argname`, so that it can be wrapped.

  ```python
  def argname2(arg, *more_args):
      return argname(arg, *more_args, frame=2)
  ```

- Allow `argname` to fetch the source of variable keyword arguments (`**kwargs`), which will be an empty dict (`{}`) when no keyword arguments passed.

  ```python
  def func(a, **kwargs):
      return argname(a, kwargs)
  # before:
  func(x) # raises error
  # after:
  func(x) # returns ('x', {})
  ```

- Add argument `pos_only` to `argname` to only match the positional arguments

  ```python
  # before
  def func(a, b=1):
    return argname(a)
  func(x) # 'x'
  func(x, b=2) # error since 2 is not ast.Name

  # after
  def func(a, b=1):
    return argname(a, pos_only=True)
  func(x) # 'x'
  func(x, b=2) # 'x'
  ```

- Parse the arguments only if needed

  ```python
  # before
  def func(a, b):
    return argname(a)
  func(x, 1) # NonVariableArgumentError

  # after
  func(x, 1) # 'x'
  ```

- Allow variable positional arguments for `argname` so that `argname(*args)` is allowed

  ```python
  # before
  def func(arg, *args):
    return argname(arg, args) # *args not allowed
  x = y = 1
  func(x, y) # ('x', ('y', 1))

  # after
  def func(arg, *args):
    return argname(arg, *args)
  x = y = 1
  func(x, y) # ('x', 'y')
  ```

- Add `vars_only` (defaults to `False`) argument to `helpers.debug` so source of expression becomes available

  ```python
  a=1
  debug(a+a) # DEBUG: a+a=2
  ```

## v0.6.1

- Add `argname` to retrieve argument names/sources passed to a function

## v0.6.0

- Changed:
  - `Wrapper`, `register` and `debug` moved to `varname.helpers`
  - Argument `caller` changed to `frame` across all APIs
  - `ignore` accepting module, filename, function, (function, num_decorators), (module, qualname) and (filename, qualname)
- Removed:
  - `inject` (Use `helpers.regiester` instead)
  - `inject_varname` (Use `helpers.regiester` instead)
  - `namedtuple`
- Added:
  - Arguments `frame` and `ignore` to `Wrapper`
  - `helpers.register` as a decorator for functions

## v0.5.6

- Add `ignore` argument to `varname` to ignore frames that are not counted by caller
- Deprecate `inject_varname`, use `register` instead

## v0.5.5

- Deprecate inject and use inject_varname decorator instead

## v0.5.4

- Allow `varname.varname` to receive multiple variables on the left-hand side

## v0.5.3

- Add `debug` function
- Deprecate `namedtuple` (will be removed in `0.6.0`)

## v0.5.2

- Move messaging of weird nameof calls from `_bytecode_nameof` to `nameof`.
- Disallow `full` to be used when `_bytecode_nameof` needs to be invoked.

## v0.5.1

- Add better messaging for weird nameof calls

## v0.5.0

- Allow `nameof` to retrieve full name of chained attribute calls
- Add `__all__` to the module so that only desired APIs are exposed when `from varname import *`
- Give more hints on `nameof` being called in a weird way when no soucecode available.

## v0.4.0

- Change default of `raise_exc` to `True` for all related APIs
- Deprecate `var_0`
- Get rid of `VarnameRetrievingWarning`.

## v0.3.0

- Use sys._getframe instead of inspect.stack for efficiency (#9)
- Add alternative way of testing bytecode nameof (#10)
- Drop support for pytest, don't try to find node when executing fails
- Remodel `will` for better logic
- Support attributes in varname and nameof (#14)

## v0.2.0

- Fix #5 and fit nameof in more cases

## v0.1.7

- Add `inject` function

## v0.1.6

- Fit situations when frames cannot be fetched
- Add shortcut for `namedtuple`

## v0.1.5

- Fix `will` from a property call

## v0.1.4

- Add `will` to detect next immediate attribute name

## v0.1.3

- Add arugment `raise_exc` for `varname` to raise an exception instead of returning `var_<index>`

## v0.1.2

- Add function `nameof`

## v0.1.1

- Add a value wrapper `Wrapper` class

## v0.1.0

- Implement `varname` function
