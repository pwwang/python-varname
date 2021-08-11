"""Provide core features for varname"""
import ast
import re
import warnings
from typing import List, Tuple, Type, Union, Callable

from executing import Source

from .utils import (
    bytecode_nameof,
    get_node,
    get_node_by_frame,
    lookfor_parent_assign,
    node_name,
    get_argument_sources,
    get_function_called_argname,
    rich_exc_message,
    ArgSourceType,
    VarnameRetrievingError,
    ImproperUseError,
    MultiTargetAssignmentWarning,
)
from .ignore import IgnoreList, IgnoreType


def varname(
    frame: int = 1,
    ignore: IgnoreType = None,
    multi_vars: bool = False,
    raise_exc: bool = True,
    strict: bool = True,
) -> Union[str, Tuple[Union[str, Tuple], ...]]:
    """Get the name of the variable(s) that assigned by function call or
    class instantiation.

    To debug and specify the right frame and ignore arguments, you can set
    debug on and see how the frames are ignored or selected:

    >>> from varname import config
    >>> config.debug = True

    Args:
        frame: `N`th frame used to retrieve the variable name. This means
            `N-1` intermediate frames will be skipped. Note that the frames
            match `ignore` will not be counted. See `ignore` for details.
        ignore: Frames to be ignored in order to reach the `N`th frame.
            These frames will not be counted to skip within that `N-1` frames.
            You can specify:
            - A module (or filename of a module). Any calls from it and its
                submodules will be ignored.
            - A function. If it looks like it might be a decorated function,
                a `MaybeDecoratedFunctionWarning` will be shown.
            - Tuple of a function and a number of additional frames that should
                be skipped just before reaching this function in the stack.
                This is typically used for functions that have been decorated
                with a 'classic' decorator that replaces the function with
                a wrapper. In that case each such decorator involved should
                be counted in the number that's the second element of the tuple.
            - Tuple of a module (or filename) and qualified name (qualname).
                You can use Unix shell-style wildcards to match the qualname.
                Otherwise the qualname must appear exactly once in the
                module/file.
            By default, all calls from `varname` package, python standard
            libraries and lambda functions are ignored.
        multi_vars: Whether allow multiple variables on left-hand side (LHS).
            If `True`, this function returns a tuple of the variable names,
            even there is only one variable on LHS.
            If `False`, and multiple variables on LHS, a
            `ImproperUseError` will be raised.
        raise_exc: Whether we should raise an exception if failed
            to retrieve the ast node.
            Note that set this to `False` will NOT supress the exception when
            the use of `varname` is improper (i.e. multiple variables on
            LHS with `multi_vars` is `False`). See `Raises/ImproperUseError`.
        strict: Whether to only return the variable name(s) if the result of
            the call is assigned to it/them directly.

    Returns:
        The variable name, or `None` when `raise_exc` is `False` and
            we failed to retrieve the ast node for the variable(s).
        A tuple or a hierarchy (tuple of tuples) of variable names
            when `multi_vars` is `True`.

    Raises:
        VarnameRetrievingError: When we are unable to retrieve the ast node
            for the variable(s) and `raise_exc` is set to `True`.

        ImproperUseError: When the use of `varname()` is improper, including:
            - When LHS is not an `ast.Name` or `ast.Attribute` node or not a
                list/tuple of them
            - When there are multiple variables on LHS but `multi_vars` is False
            - When `strict` is True, but the result is not assigned to
                variable(s) directly

            Note that `raise_exc=False` will NOT suppress this exception.

        MultiTargetAssignmentWarning: When there are multiple target
            in the assign node. (e.g: `a = b = func()`, in such a case,
            `a == 'b'`, may not be the case you want)
    """
    # Skip one more frame, as it is supposed to be called
    # inside another function
    refnode = get_node(frame + 1, ignore, raise_exc=raise_exc)
    if not refnode:
        if raise_exc:
            raise VarnameRetrievingError("Unable to retrieve the ast node.")
        return None

    node = lookfor_parent_assign(refnode, strict=strict)
    if not node:  # improper use
        if strict:
            msg = "Caller doesn't assign the result directly to variable(s)."
        else:
            msg = "Expression is not part of an assignment."

        raise ImproperUseError(rich_exc_message(msg, refnode))

    if isinstance(node, ast.Assign):
        # Need to actually check that there's just one
        # give warnings if: a = b = func()
        if len(node.targets) > 1:
            warnings.warn(
                "Multiple targets in assignment, variable name "
                "on the very right is used. ",
                MultiTargetAssignmentWarning,
            )
        target = node.targets[-1]
    else:
        target = node.target

    names = node_name(target)

    if not isinstance(names, tuple):
        names = (names,)

    if multi_vars:
        return names

    if len(names) > 1:
        raise ImproperUseError(
            rich_exc_message(
                "Expect a single variable on left-hand side, "
                f"got {len(names)}.",
                refnode,
            )
        )

    return names[0]


def will(frame: int = 1, raise_exc: bool = True) -> str:
    """Detect the attribute name right immediately after a function call.

    Examples:
        >>> class AwesomeClass:
        >>>     def __init__(self):
        >>>         self.will = None

        >>>     def permit(self):
        >>>         self.will = will()
        >>>         if self.will == 'do':
        >>>             # let self handle do
        >>>             return self
        >>>         raise AttributeError(
        >>>             'Should do something with AwesomeClass object'
        >>>         )

        >>>     def do(self):
        >>>         if self.will != 'do':
        >>>             raise AttributeError("You don't have permission to do")
        >>>         return 'I am doing!'

        >>> awesome = AwesomeClass()
        >>> # AttributeError: You don't have permission to do
        >>> awesome.do()
        >>> # AttributeError: Should do something with AwesomeClass object
        >>> awesome.permit()
        >>> awesome.permit().do() == 'I am doing!'

    Args:
        frame: At which frame this function is called.
        raise_exc: Raise exception we failed to detect the ast node
            This will NOT supress the `ImproperUseError`

    Returns:
        The attribute name right after the function call.
        `None` if ast node cannot be retrieved and `raise_exc` is `False`

    Raises:
        VarnameRetrievingError: When `raise_exc` is `True` and we failed to
            detect the attribute name (including not having one)

        ImproperUseError: When (the wraper of) this function is not called
            inside a method/property of a class instance.
            Note that this exception will not be suppressed by `raise_exc=False`
    """
    node = get_node(frame + 1, raise_exc=raise_exc)
    if not node:
        if raise_exc:
            raise VarnameRetrievingError("Unable to retrieve the frame.")
        return None

    # try to get node inst.attr from inst.attr()
    node = node.parent

    # see test_will_fail
    if not isinstance(node, ast.Attribute):
        if raise_exc:
            raise ImproperUseError(
                "Function `will` has to be called within "
                "a method/property of a class."
            )
        return None
    # ast.Attribute
    return node.attr


def nameof(
    var,  # pylint: disable=unused-argument
    *more_vars,
    # *, keyword only argument, supported with python3.8+
    frame: int = 1,
    vars_only: bool = True,
) -> Union[str, Tuple[str, ...]]:
    """Get the names of the variables passed in

    Examples:
        >>> a = 1
        >>> nameof(a) # 'a'

        >>> b = 2
        >>> nameof(a, b) # ('a', 'b')

        >>> x = lambda: None
        >>> x.y = 1
        >>> nameof(x.y, full=True) # 'x.y'

    Note:
        This function works with the environments where source code is
        available, in other words, the callee's node can be retrieved by
        `executing`. In some cases, for example, running code from python
        shell/REPL or from `exec`/`eval`, we try to fetch the variable name
        from the bytecode. This requires only a single variable name is passed
        to this function and no keyword arguments, meaning that getting full
        names of attribute calls are not supported in such cases.

    Args:
        var: The variable to retrieve the name of
        *more_vars: Other variables to retrieve the names of
        frame: The this function is called from the wrapper of it. `frame=1`
            means no wrappers.
            Note that the calls from standard libraries are ignored.
            Also note that the wrapper has to have signature as this one.
        vars_only: Whether only allow variables/attributes as arguments or
            any expressions. If `True`, then the sources of the arguments
            will be returned.

    Returns:
        The names/sources of variables/expressions passed in.
            If a single argument is passed, return the name/source of it.
            If multiple variables are passed, return a tuple of their
            names/sources.
            If the argument is an attribute (e.g. `a.b`) and `vars_only` is
            `False`, only `"b"` will returned. Set `vars_only` to `True` to
            get `"a.b"`.

    Raises:
        VarnameRetrievingError: When the callee's node cannot be retrieved or
            trying to retrieve the full name of non attribute series calls.
    """
    # Frame is anyway used in get_node
    frameobj = IgnoreList.create(
        ignore_lambda=False,
        ignore_varname=False,
    ).get_frame(frame)

    node = get_node_by_frame(frameobj, raise_exc=True)
    if not node:
        # We can't retrieve the node by executing.
        # It can be due to running code from python/shell, exec/eval or
        # other environments where sourcecode cannot be reached
        # make sure we keep it simple (only single variable passed and no
        # full passed) to use bytecode_nameof
        #
        # We don't have to check keyword arguments here, as the instruction
        # will then be CALL_FUNCTION_KW.
        if not more_vars:
            return bytecode_nameof(frameobj.f_code, frameobj.f_lasti)

        # We are anyway raising exceptions, no worries about additional burden
        # of frame retrieval again
        source = frameobj.f_code.co_filename
        if source == "<stdin>":
            raise VarnameRetrievingError(
                "Are you trying to call nameof in REPL/python shell? "
                "In such a case, nameof can only be called with single "
                "argument and no keyword arguments."
            )
        if source == "<string>":
            raise VarnameRetrievingError(
                "Are you trying to call nameof from exec/eval? "
                "In such a case, nameof can only be called with single "
                "argument and no keyword arguments."
            )
        raise VarnameRetrievingError(
            "Source code unavailable, nameof can only retrieve the name of "
            "a single variable, and argument `full` should not be specified."
        )

    out = argname(
        "var",
        "*more_vars",
        func=nameof,
        frame=frame,
        vars_only=vars_only,
    )
    return out if more_vars else out[0]  # type: ignore


def argname(  # pylint: disable=too-many-branches
    arg: str,
    *more_args: str,
    # *, keyword-only argument, only available with python3.8+
    func: Callable = None,
    dispatch: Type = None,
    frame: int = 1,
    ignore: IgnoreType = None,
    vars_only: bool = True,
) -> ArgSourceType:
    """Get the names/sources of arguments passed to a function.

    Instead of passing the argument variables themselves to this function
    (like `argname()` does), you should pass their names instead.

    Args:
        arg: and
        *more_args: The names of the arguments that you want to retrieve
            names/sources of.
            You can also use subscripts to get parts of the results.
            >>> def func(*args, **kwargs):
            >>>     return argname2('args[0]', 'kwargs[x]') # no quote needed

            Star argument is also allowed:
            >>> def func(*args, x = 1):
            >>>     return argname2('*args', 'x')
            >>> a = b = c = 1
            >>> func(a, b, x=c) # ('a', 'b', 'c')

            Note the difference:
            >>> def func(*args, x = 1):
            >>>     return argname2('args', 'x')
            >>> a = b = c = 1
            >>> func(a, b, x=c) # (('a', 'b'), 'c')

        func: The target function. If not provided, the AST node of the
            function call will be used to fetch the function:
            - If a variable (ast.Name) used as function, the `node.id` will
                be used to get the function from `locals()` or `globals()`.
            - If variable (ast.Name), attributes (ast.Attribute),
                subscripts (ast.Subscript), and combinations of those and
                literals used as function, `pure_eval` will be used to evaluate
                the node
            - If `pure_eval` is not installed or failed to evaluate, `eval`
                will be used. A warning will be shown since unwanted side
                effects may happen in this case.
            You are very encouraged to always pass the function explicitly.
        dispatch: If a function is a single-dispatched function, you can
            specify a type for it to dispatch the real function. If this is
            specified, expect `func` to be the generic function if provided.
        frame: The frame where target function is called from this call.
            Calls from python standard libraries are ignored.
        ignore: The intermediate calls to be ignored. See `varname.ignore`
        vars_only: Require the arguments to be variables only.
            If False, `asttokens` is required to retrieve the source.

    Returns:
        The argument source when no more_args passed, otherwise a tuple of
        argument sources

    Raises:
        VarnameRetrievingError: When the ast node where the function is called
            cannot be retrieved
    """
    ignore_list = IgnoreList.create(
        ignore,
        ignore_lambda=False,
        ignore_varname=False,
    )
    # where func(...) is called, skip the argname2() call
    func_frame = ignore_list.get_frame(frame + 1)
    func_node = get_node_by_frame(func_frame)
    # Only do it when func_node are available
    if not func_node:
        # We can do something at bytecode level, when a single positional
        # argument passed to both functions (argname and the target function)
        # However, it's hard to ensure that there is only a single positional
        # arguments passed to the target function, at bytecode level.
        raise VarnameRetrievingError(
            "Cannot retrieve the node where the function is called."
        )

    if not func:
        func = get_function_called_argname(func_frame, func_node)

    if dispatch:
        func = func.dispatch(dispatch)

    # don't pass the target arguments so that we can cache the sources in
    # the same call. For example:
    # >>> def func(a, b):
    # >>>   a_name = argname(a)
    # >>>   b_name = argname(b)
    try:
        argument_sources = get_argument_sources(
            Source.for_frame(func_frame),
            func_node,
            func,
            vars_only=vars_only,
        )
    except Exception as err:  # pragma: no cover
        # find a test case?
        raise VarnameRetrievingError(
            "Have you specified the right `frame`?"
        ) from err

    out = []  # type: List[ArgSourceType]
    farg_star = False
    for farg in (arg, *more_args):

        farg_name = farg
        farg_subscript = None  # type: str | int
        match = re.match(r"^([\w_]+)\[(.+)\]$", farg)
        if match:
            farg_name = match.group(1)
            farg_subscript = match.group(2)
            if farg_subscript.isdigit():
                farg_subscript = int(farg_subscript)
        else:
            match = re.match(r"^\*([\w_]+)$", farg)
            if match:
                farg_name = match.group(1)
                farg_star = True

        if farg_name not in argument_sources:
            raise ImproperUseError(
                f"{farg_name!r} is not a valid argument "
                f"of {func.__qualname__!r}."
            )

        source = argument_sources[farg_name]
        if isinstance(source, ast.AST):
            raise ImproperUseError(
                f"Argument {ast.dump(source)} is not a variable "
                "or an attribute."
            )

        if isinstance(farg_subscript, int) and not isinstance(source, tuple):
            raise ImproperUseError(
                f"`{farg_name}` is not a positional argument."
            )

        if isinstance(farg_subscript, str) and not isinstance(source, dict):
            raise ImproperUseError(
                f"`{farg_name}` is not a keyword argument."
            )

        if farg_subscript is not None:
            out.append(source[farg_subscript])  # type: ignore
        elif farg_star:
            out.extend(source)
        else:
            out.append(source)

    return (
        out[0]
        if not more_args and not farg_star
        else tuple(out)  # type: ignore
    )


def argname2(
    arg: str,
    *more_args: str,
    # *, keyword-only argument, only available with python3.8+
    func: Callable = None,
    dispatch: Type = None,
    frame: int = 1,
    ignore: IgnoreType = None,
    vars_only: bool = True,
) -> ArgSourceType:
    """Alias of argname, will be removed in v0.9.0"""
    warnings.warn(
        "`argname2()` is deprecated and will be removed in v0.9.0. "
        "Use `argname()` instead.",
        DeprecationWarning
    )
    return argname(
        arg,
        *more_args,
        func=func,
        dispatch=dispatch,
        frame=frame+1,
        ignore=ignore,
        vars_only=vars_only,
    )
