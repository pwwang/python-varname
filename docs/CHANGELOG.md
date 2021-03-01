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
