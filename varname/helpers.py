"""Some helper functions builtin based upon core features"""
import inspect
from functools import partial, wraps
from typing import Any, Callable, Type, Union

from .utils import IgnoreType
from .core import argname, varname


def register(
    cls_or_func: type = None,
    # *, keyword-only argument, only available with python3.8+
    frame: int = 1,
    ignore: IgnoreType = None,
    multi_vars: bool = False,
    raise_exc: bool = True,
    strict: bool = True,
) -> Union[Type, Callable]:
    """A decorator to register __varname__ to a class or function

    When registered to a class, it can be accessed by `self.__varname__`;
    while to a function, it is registered to globals, meaning that it can be
    accessed directly.

    Args:
        frame: The call stack index, indicating where this class
            is instantiated relative to where the variable is finally retrieved
        multi_vars: Whether allow multiple variables on left-hand side (LHS).
            If `True`, this function returns a tuple of the variable names,
            even there is only one variable on LHS.
            If `False`, and multiple variables on LHS, a
            `VarnameRetrievingError` will be raised.
        raise_exc: Whether we should raise an exception if failed
            to retrieve the name.
        strict: Whether to only return the variable name if the result of
            the call is assigned to it directly.

    Examples:
        >>> @varname.register
        >>> class Foo: pass
        >>> foo = Foo()
        >>> # foo.__varname__ == 'foo'
        >>>
        >>> @varname.register
        >>> def func():
        >>>   return __varname__
        >>> foo = func() # foo == 'foo'

    Returns:
        The wrapper function or the class/function itself
        if it is specified explictly.
    """
    if inspect.isclass(cls_or_func):
        orig_init = cls_or_func.__init__  # type: ignore

        @wraps(cls_or_func.__init__)  # type: ignore
        def wrapped_init(self, *args, **kwargs):
            """Wrapped init function to replace the original one"""
            self.__varname__ = varname(
                frame - 1,
                ignore=ignore,
                multi_vars=multi_vars,
                raise_exc=raise_exc,
                strict=strict,
            )
            orig_init(self, *args, **kwargs)

        cls_or_func.__init__ = wrapped_init  # type: ignore
        return cls_or_func

    if inspect.isfunction(cls_or_func):

        @wraps(cls_or_func)
        def wrapper(*args, **kwargs):
            """The wrapper to register `__varname__` to a function"""
            cls_or_func.__globals__["__varname__"] = varname(
                frame - 1,
                ignore=ignore,
                multi_vars=multi_vars,
                raise_exc=raise_exc,
                strict=strict,
            )

            try:
                return cls_or_func(*args, **kwargs)
            finally:
                del cls_or_func.__globals__["__varname__"]

        return wrapper

    # None, meaning we have other arguments
    return partial(
        register,
        frame=frame,
        ignore=ignore,
        multi_vars=multi_vars,
        raise_exc=raise_exc,
        strict=strict,
    )


class Wrapper:
    """A wrapper with ability to retrieve the variable name

    Examples:
        >>> foo = Wrapper(True)
        >>> # foo.name == 'foo'
        >>> # foo.value == True

        >>> val = {}
        >>> bar = Wrapper(val)
        >>> # bar.name == 'bar'
        >>> # bar.value is val

    Args:
        value: The value to be wrapped
        raise_exc: Whether to raise exception when varname is failed to retrieve
        strict: Whether to only return the variable name if the wrapper is
            assigned to it directly.

    Attributes:
        name: The variable name to which the instance is assigned
        value: The value this wrapper wraps
    """

    def __init__(
        self,
        value: Any,
        frame: int = 1,
        ignore: IgnoreType = None,
        raise_exc: bool = True,
        strict: bool = True,
    ):
        # This call is ignored, since it's inside varname
        self.name = varname(
            frame=frame - 1,
            ignore=ignore,
            raise_exc=raise_exc,
            strict=strict,
        )
        self.value = value

    def __str__(self) -> str:
        return repr(self.value)

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"(name={self.name!r}, value={self.value!r})>"
        )


def debug(
    var,
    *more_vars,
    prefix: str = "DEBUG: ",
    merge: bool = False,
    repr: bool = True,  # pylint: disable=redefined-builtin
    sep: str = "=",
    vars_only: bool = False,
) -> None:
    """Print variable names and values.

    Examples:
        >>> a = 1
        >>> b = object
        >>> print(f'a={a}') # previously, we have to do
        >>> print(f'{a=}')  # or with python3.8
        >>> # instead we can do:
        >>> debug(a) # DEBUG: a=1
        >>> debug(a, prefix='') # a=1
        >>> debug(a, b, merge=True) # a=1, b=<object object at 0x2b9a4c89cf00>

    Args:
        var: The variable to print
        *more_vars: Other variables to print
        prefix: A prefix to print for each line
        merge: Whether merge all variables in one line or not
        sep: The separator between the variable name and value
        repr: Print the value as `repr(var)`? otherwise `str(var)`
    """
    var_names = argname("var", "*more_vars", vars_only=vars_only, func=debug)

    values = (var, *more_vars)
    name_and_values = [
        f"{var_name}{sep}{value!r}" if repr else f"{var_name}{sep}{value}"
        for var_name, value in zip(var_names, values)  # type: ignore
    ]

    if merge:
        print(f"{prefix}{', '.join(name_and_values)}")
    else:
        for name_and_value in name_and_values:
            print(f"{prefix}{name_and_value}")
