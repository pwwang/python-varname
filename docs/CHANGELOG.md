## v0.1.0
- Implement `varname` function

## v0.1.1
- Add a value wrapper `Wrapper` class

## v0.1.2
- Add function `nameof`

## v0.1.3
- Add arugment `raise_exc` for `varname` to raise an exception instead of returning `var_<index>`

## v0.1.4
- Add `will` to detect next immediate attribute name

## v0.1.5
- Fix `will` from a property call

## v0.1.6
- Fit situations when frames cannot be fetched
- Add shortcut for `namedtuple`

## v0.1.7
- Add `inject` function

## v0.2.0
- Fix #5 and fit nameof in more cases

## v0.3.0
- Use sys._getframe instead of inspect.stack for efficiency (#9)
- Add alternative way of testing bytecode nameof (#10)
- Drop support for pytest, don't try to find node when executing fails
- Remodel `will` for better logic
- Support attributes in varname and nameof (#14)

## v0.4.0
- Change default of `raise_exc` to `True` for all related APIs
- Deprecate `var_0`
- Get rid of `VarnameRetrievingWarning`.

## v0.5.0
- Allow `nameof` to retrieve full name of chained attribute calls
- Add `__all__` to the module so that only desired APIs are exposed when `from varname import *`
- Give more hints on `nameof` being called in a weird way when no soucecode available.
