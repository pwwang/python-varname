"""Provide core features for varname"""
import ast
import warnings
from typing import Optional, Tuple, Union, Any, Callable

from executing import Source

from .utils import (
    bytecode_nameof,
    get_node,
    get_node_by_frame,
    lookfor_parent_assign,
    node_name,
    get_argument_sources,
    get_function_called_argname,
    parse_argname_subscript,
    VarnameRetrievingError,
    NonVariableArgumentError,
    MultiTargetAssignmentWarning
)
from .ignore import IgnoreList, IgnoreType

def varname(
        frame: int = 1,
        ignore: Optional[IgnoreType] = None,
        multi_vars: bool = False,
        raise_exc: bool = True
) -> Optional[Union[str, Tuple[Union[str, tuple]]]]:
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
            `VarnameRetrievingError` will be raised.
        raise_exc: Whether we should raise an exception if failed
            to retrieve the name.

    Returns:
        The variable name, or `None` when `raise_exc` is `False` and
            we failed to retrieve the variable name.
        A tuple or a hierarchy (tuple of tuples) of variable names
            when `multi_vars` is `True`.

    Raises:
        VarnameRetrievingError: When there is invalid variables or
            invalid number of variables used on the LHS; or
            when we are unable to retrieve the variable name and `raise_exc`
            is set to `True`.

        UserWarning: When there are multiple target
            in the assign node. (e.g: `a = b = func()`, in such a case,
            `b == 'a'`, may not be the case you want)
    """
    # Skip one more frame, as it is supposed to be called
    # inside another function
    node = get_node(frame + 1, ignore, raise_exc=raise_exc)
    if not node:
        if raise_exc:
            raise VarnameRetrievingError("Unable to retrieve the ast node.")
        return None

    node = lookfor_parent_assign(node)
    if not node:
        if raise_exc:
            raise VarnameRetrievingError(
                'Failed to retrieve the variable name.'
            )
        return None

    if isinstance(node, ast.AnnAssign):
        target = node.target
    else:
        # Need to actually check that there's just one
        # give warnings if: a = b = func()
        if len(node.targets) > 1:
            warnings.warn("Multiple targets in assignment, variable name "
                          "on the very left will be used.",
                          MultiTargetAssignmentWarning)
        target = node.targets[0]

    names = node_name(target)

    if not isinstance(names, tuple):
        names = (names, )

    if multi_vars:
        return names

    if len(names) > 1:
        raise VarnameRetrievingError(
            f"Expect a single variable on left-hand side, got {len(names)}."
        )

    return names[0]

def will(frame: int = 1, raise_exc: bool = True) -> Optional[str]:
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
        raise_exc: Raise exception we failed to detect

    Returns:
        The attribute name right after the function call
        If there is no attribute attached and `raise_exc` is `False`

    Raises:
        VarnameRetrievingError: When `raise_exc` is `True` and we failed to
            detect the attribute name (including not having one)
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
            raise VarnameRetrievingError(
                "Function `will` has to be called within "
                "a method/property of a class."
            )
        return None
    # ast.Attribute
    return node.attr


def nameof(var, *more_vars,
           # *, keyword only argument, supported with python3.8+
           frame: int = 1,
           vars_only: bool = True) -> Union[str, Tuple[str]]:
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
        ignore_varname=False
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
        if source == '<stdin>':
            raise VarnameRetrievingError(
                "Are you trying to call nameof in REPL/python shell? "
                "In such a case, nameof can only be called with single "
                "argument and no keyword arguments."
            )
        if source == '<string>':
            raise VarnameRetrievingError(
                "Are you trying to call nameof from exec/eval? "
                "In such a case, nameof can only be called with single "
                "argument and no keyword arguments."
            )
        raise VarnameRetrievingError(
            "Source code unavailable, nameof can only retrieve the name of "
            "a single variable, and argument `full` should not be specified."
        )

    return argname(
        var, *more_vars,
        func=nameof,
        frame=frame,
        vars_only=vars_only,
        pos_only=True
    )

def argname(arg: Any, # pylint: disable=unused-argument
            *more_args: Any,
            # *, keyword-only argument, only available with python3.8+
            func: Optional[Callable] = None,
            frame: int = 1,
            vars_only: bool = True,
            pos_only: bool = False) -> Union[str, Tuple[str]]:
    """Get the argument names/sources passed to a function

    Args:
        arg: Parameter of the function, used to map the argument passed to
            the function
        *more_args: Other parameters of the function, used to map more arguments
            passed to the function
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
            You are encouraged to always pass the function explicitly.
        frame: The frame where target function is called from this call.
            The intermediate calls will be the wrappers of this function.
            However, keep in mind that the wrappers must have the same
            signature as this function. When `pos_only` is `True`, only the
            positional arguments have to be the same
        vars_only: Require the arguments to be variables only,
        pos_only: Only fetch the names/sources for positional arguments.

    Returns:
        The argument source when no more_args passed, otherwise a tuple of
        argument sources

    Raises:
        NonVariableArgumentError: When vars_only is True, and we are trying
            to retrieve the source of an argument that is not a variable
            (i.e. an expression)
        VarnameRetrievingError: When failed to get the frame or node
        ValueError: When the arguments passed to this function is invalid.
            Only variables and subscripts of variables are allow to be passed
            to this function.
    """
    ignore_list = IgnoreList.create(
        ignore_lambda=False,
        ignore_varname=False
    )
    # where argname(...) is called
    argname_frame = ignore_list.get_frame(frame)
    argname_node = get_node_by_frame(argname_frame)
    # where func(...) is called
    func_frame = ignore_list.get_frame(frame + 1)
    func_node = get_node_by_frame(func_frame)
    # Only do it when both nodes are available
    if not argname_node or not func_node:
        # We can do something at bytecode level, when a single positional
        # argument passed to both functions (argname and the target function)
        # However, it's hard to ensure that there is only a single positional
        # arguments passed to the target function, at bytecode level.
        raise VarnameRetrievingError(
            "The source code of 'argname' calling is not available."
        )

    if not func:
        func = get_function_called_argname(func_frame, func_node)

    # don't pass the target arguments so that we can cache the sources in
    # the same call. For example:
    # >>> def func(a, b):
    # >>>   a_name = argname(a)
    # >>>   b_name = argname(b)
    argument_sources = get_argument_sources(
        Source.for_frame(func_frame),
        func_node,
        func,
        vars_only=vars_only,
        pos_only=pos_only
    )

    ret = []
    for argnode in argname_node.args:
        if not isinstance(argnode, (ast.Name, ast.Subscript, ast.Starred)):
            raise ValueError(
                "Arguments of 'argname' must be "
                "function arguments themselves or subscripts of them."
            )

        if isinstance(argnode, ast.Starred):
            if (
                    not isinstance(argnode.value, ast.Name) or
                    argnode.value.id not in argument_sources or
                    not isinstance(argument_sources[argnode.value.id], tuple)
            ):
                posvar = argnode.value
                posvar = getattr(posvar, 'id', posvar)
                raise ValueError(
                    f"No such variable positional argument {posvar!r}"
                )
            ret.extend(argument_sources[argnode.value.id])

        elif isinstance(argnode, ast.Name):
            if argnode.id not in argument_sources:
                raise ValueError(
                    f"No value passed for argument {argnode.id!r}, "
                    "or it is not an argument at all."
                )
            ret.append(argument_sources[argnode.id])

        else:
            name, subscript = parse_argname_subscript(argnode)
            if name not in argument_sources:
                raise ValueError(f"{name!r} is not an argument.")

            if (isinstance(subscript, int) and
                    not isinstance(argument_sources[name], tuple)):
                raise ValueError(
                    f"{name!r} is not a positional argument "
                    "(*args, for example)."
                )
            if (isinstance(subscript, str) and
                    not isinstance(argument_sources[name], dict)):
                raise ValueError(
                    f"{name!r} is not a keyword argument "
                    "(**kwargs, for example)."
                )
            ret.append(argument_sources[name][subscript])

    if vars_only:
        for source in ret:
            if isinstance(source, ast.AST):
                raise NonVariableArgumentError(
                    f'Argument {ast.dump(source)} is not a variable '
                    'or an attribute.'
                )

    return ret[0] if not more_args else tuple(ret)
