"""Provide core features for varname"""

import ast
import warnings
from typing import Optional, Tuple, Union
from .utils import (
    bytecode_nameof,
    get_node,
    lookfor_parent_assign,
    node_name,
    VarnameRetrievingError,
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


def nameof(var, *more_vars, # pylint: disable=unused-argument
           frame: int = 1,
           full: Optional[bool] = None) -> Union[str, Tuple[str]]:
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
        frame: The depth of the frame (this function) is called.
            This is useful if you want to wrap this function.
            Note that the calls from varname and builtin modules are ignored.
        full: Whether report the full path of the variable.
            For example: `nameof(a.b.c, full=True)` give you `a.b.c`
            instead of `c`

    Returns:
        The names of variables passed in. If a single varialble is passed,
            return the name of it. If multiple variables are passed, return
            a tuple of their names.

    Raises:
        VarnameRetrievingError: When the callee's node cannot be retrieved or
            trying to retrieve the full name of non attribute series calls.
    """
    node = get_node(frame, raise_exc=True)
    if not node:
        # We can't retrieve the node by executing.
        # It can be due to running code from python/shell, exec/eval or
        # other environments where sourcecode cannot be reached
        # make sure we keep it simple (only single variable passed and no
        # full passed) to use _bytecode_nameof
        if not more_vars and full is None:
            return bytecode_nameof(frame)

        # We are anyway raising exceptions, no worries about additional burden
        # of frame retrieval again

        # may raise exception, just leave it as is
        frame = IgnoreList.create(None).get_frame(frame)
        source = frame.f_code.co_filename
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

    ret = []
    for arg in node.args:
        if not full or isinstance(arg, ast.Name):
            ret.append(node_name(arg))
        else:
            # traverse the node to get the full name: nameof(a.b.c)
            # arg:
            # Attribute(value=Attribute(value=Name(id='a', ctx=Load()),
            #                           attr='b',
            #                           ctx=Load()),
            #           attr='c',
            #           ctx=Load())
            full_name = []
            while not isinstance(arg, ast.Name):
                if not isinstance(arg, ast.Attribute):
                    raise VarnameRetrievingError(
                        'Can only retrieve full names of '
                        '(chained) attribute calls by nameof.'
                    )
                full_name.append(arg.attr)
                arg = arg.value
            # now it is an ast.Name
            full_name.append(arg.id)
            ret.append('.'.join(reversed(full_name)))

    return ret[0] if not more_vars else tuple(ret)
