"""Dark magics about variable name in python"""
import ast
import dis
import sys
import inspect
import warnings
from typing import Callable, List, Union, Tuple, Any, Optional
from types import FrameType, CodeType, ModuleType
from collections import namedtuple as standard_namedtuple
from functools import wraps, lru_cache

import executing

__version__ = "0.5.6"
__all__ = [
    "VarnameRetrievingError", "varname", "will", "inject_varname",
    "register", "inject", "nameof", "namedtuple", "Wrapper", "debug"
]

# To show how the desired frame is selected and other frames are skipped
DEBUG = False

class VarnameRetrievingError(Exception):
    """When failed to retrieve the varname"""

def varname(
        caller: int = 1,
        ignore: Optional[
            List[Union[ModuleType, Tuple[ModuleType, str]]]
        ] = None,
        multi_vars: bool = False,
        raise_exc: bool = True
) -> Optional[Union[str, Tuple[Union[str, tuple]]]]:
    """Get the variable name that assigned by function/class calls

    To debug and specify the right caller and ignore arguments, you can set
    debug on and see how the frames are ignored or selected:

    >>> import varname
    >>> varname.DEBUG = True

    Args:
        caller: The call frame index, indicating where this function
            is called relative to where the variable is finally retrieved
            Frames are counted with the ignored ones being excluded.
            See `ignore` for frames to be ignored.
        ignore: A list of modules or tuples of module and qualname that
            you want to ignore for the intermediate calls.
            For example, `['module']` ignores all intermediate calls
            from `module` and its submodules, but `[(module, 'func')]`
            only ignores the calls (qual)named `func` from `module`.
            By default, all calls from `varname` and builtin modules
            (in `sys.builtin_module_names`) are ignored.
            Note that the qualname in the module should exist and be unique.
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
    ignore = ignore or []
    _check_qualname(ignore)
    # Skip one more frame, as it is supposed to be called
    # inside another function
    node = _get_node(caller + 1, ignore, raise_exc=raise_exc)
    if not node:
        if raise_exc:
            raise VarnameRetrievingError("Unable to retrieve the ast node.")
        return None

    node = _lookfor_parent_assign(node)
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
                          UserWarning)
        target = node.targets[0]

    names = _node_name(target)

    if not isinstance(names, tuple):
        names = (names, )

    if multi_vars:
        return names

    if len(names) > 1:
        raise VarnameRetrievingError(
            f"Expecting a single variable on left-hand side, got {len(names)}."
        )

    return names[0]

def will(caller: int = 1, raise_exc: bool = True) -> Optional[str]:
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
        caller: At which stack this function is called.
        raise_exc: Raise exception we failed to detect

    Returns:
        The attribute name right after the function call
        If there is no attribute attached and `raise_exc` is `False`

    Raises:
        VarnameRetrievingError: When `raise_exc` is `True` and we failed to
            detect the attribute name (including not having one)
    """
    node = _get_node(caller + 1, raise_exc=raise_exc)
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

def register(
        cls: type = None, *,
        caller: int = 1,
        multi_vars: bool = False,
        raise_exc: bool = True
) -> Union[type, Callable[[type], type]]:
    """A decorator to inject __varname__ attribute to a class

    Args:
        caller: The call stack index, indicating where this class
            is instantiated relative to where the variable is finally retrieved
        multi_vars: Whether allow multiple variables on left-hand side (LHS).
            If `True`, this function returns a tuple of the variable names,
            even there is only one variable on LHS.
            If `False`, and multiple variables on LHS, a
            `VarnameRetrievingError` will be raised.
        raise_exc: Whether we should raise an exception if failed
            to retrieve the name.

    Examples:
        >>> @varname.register
        >>> class Foo: pass
        >>> foo = Foo()
        >>> # foo.__varname__ == 'foo'

    Returns:
        The wrapper function or the class itself if it is specified explictly.
    """

    if cls is not None:
        # Used as @register directly
        return register(
            caller=caller,
            multi_vars=multi_vars,
            raise_exc=raise_exc
        )(cls)

    # Used as @register(multi_vars=..., raise_exc=...)
    def wrapper(cls):
        """The wrapper function to wrap a class and inject `__varname__`"""
        orig_init = cls.__init__

        @wraps(cls.__init__)
        def wrapped_init(self, *args, **kwargs):
            """Wrapped init function to replace the original one"""
            self.__varname__ = varname(
                caller=caller-1,
                multi_vars=multi_vars,
                raise_exc=raise_exc
            )
            orig_init(self, *args, **kwargs)

        cls.__init__ = wrapped_init
        return cls

    return wrapper

def inject_varname(
        cls: type = None, *,
        caller: int = 1,
        multi_vars: bool = False,
        raise_exc: bool = True
) -> Union[type, Callable[[type], type]]:
    """Alias of register. Will be deprecated"""
    warnings.warn("Decorator inject_varname will be removed in 0.6.0. "
                  "Use varname.register to decorate your class.",
                  DeprecationWarning)
    return register(
        cls,
        caller=caller,
        multi_vars=multi_vars,
        raise_exc=raise_exc
    )

def inject(obj: object) -> object:
    """Inject attribute `__varname__` to an object

    Examples:
        >>> class MyList(list):
        >>>     pass

        >>> a = varname.inject(MyList())
        >>> b = varname.inject(MyList())

        >>> a.__varname__ == 'a'
        >>> b.__varname__ == 'b'

        >>> a == b

        >>> # other methods not affected
        >>> a.append(1)
        >>> b.append(1)
        >>> a == b

    Args:
        obj: An object that can be injected

    Raises:
        VarnameRetrievingError: When `__varname__` is unable to
            be set as an attribute

    Returns:
        The object with __varname__ injected
    """
    warnings.warn("Function inject will be removed in 0.6.0. Use "
                  "varname.register to decorate your class.",
                  DeprecationWarning)
    vname = varname(caller=0)
    try:
        setattr(obj, '__varname__', vname)
    except AttributeError:
        raise VarnameRetrievingError('Unable to inject __varname__.') from None
    return obj


def nameof(var, *more_vars, # pylint: disable=unused-argument
           caller: int = 1,
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
        caller: The depth of the caller (this function) is called.
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
    node = _get_node(caller, raise_exc=True)
    if not node:
        # We can't retrieve the node by executing.
        # It can be due to running code from python/shell, exec/eval or
        # other environments where sourcecode cannot be reached
        # make sure we keep it simple (only single variable passed and no
        # full passed) to use _bytecode_nameof
        if not more_vars and full is None:
            # don't need caller + 1
            # since this is happening inside varname
            # and will be ignored by default
            return _bytecode_nameof(caller)

        # We are anyway raising exceptions, no worries about additional burden
        # of frame retrieval again

        # may raise exception, just leave it as is
        frame = _get_frame(caller)
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
            ret.append(_node_name(arg))
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

def debug(var, *more_vars,
          prefix: str = 'DEBUG: ',
          merge: bool = False,
          repr: bool = True) -> None: # pylint: disable=redefined-builtin
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
        repr: Print the value as `repr(var)`? otherwise `str(var)`
    """
    var_names = nameof(var, *more_vars, full=True)
    if not isinstance(var_names, tuple):
        var_names = (var_names, )
    variables = (var, *more_vars)
    name_and_values = [f"{var_name}={variables[i]!r}" if repr
                       else f"{var_name}={variables[i]}"
                       for i, var_name in enumerate(var_names)]
    if merge:
        print(f"{prefix}{', '.join(name_and_values)}")
    else:
        for name_and_value in name_and_values:
            print(f"{prefix}{name_and_value}")

def namedtuple(*args, **kwargs) -> type:
    """A shortcut for namedtuple

    You don't need to specify the typename, which will be fetched from
    the variable name.

    So instead of:
        >>> from collections import namedtuple
        >>> Name = namedtuple('Name', ['first', 'last'])

    You can do:
        >>> from varname import namedtuple
        >>> Name = namedtuple(['first', 'last'])

    Args:
        *args: arguments for `collections.namedtuple` except `typename`
        **kwargs: keyword arguments for `collections.namedtuple`
            except `typename`

    Returns:
        The namedtuple you desired.
    """
    warnings.warn("Shortcut for namedtuple is deprecated and "
                  "will be removed in 0.6.0. Use the standard way instead.",
                  DeprecationWarning)
    typename = varname(raise_exc=True)
    return standard_namedtuple(typename, *args, **kwargs)

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

    Attributes:
        name: The variable name to which the instance is assigned
        value: The value this wrapper wraps
    """

    def __init__(self, value: Any, raise_exc: bool = True):
        # This call is ignored, since it's inside varname
        self.name = varname(caller=0, raise_exc=raise_exc)
        self.value = value

    def __str__(self) -> str:
        return repr(self.value)

    def __repr__(self) -> str:
        return (f"<{self.__class__.__name__} "
                f"(name={self.name!r}, value={self.value!r})>")

def _check_qualname(
        ignore_list: List[Union[ModuleType, Tuple[ModuleType, str]]]
) -> None:
    """Check if a qualname refers to a unique object.

    If multiple or none, raise an error
    """
    assert isinstance(ignore_list, list), (
        f"A list expected for 'ignore', got {type(ignore_list)}"
    )
    for ignore_elem in ignore_list:
        if not isinstance(ignore_elem, tuple):
            continue
        module, qualname = ignore_elem
        source = executing.Source.for_filename(module.__file__, module.__dict__)
        nobj = list(source._qualnames.values()).count(qualname)
        assert nobj == 1, (
            f"Qualname {qualname!r} in {module.__name__!r} doesn't exist or "
            "refers to multiple objects."
        )

def _debug(msg: str, frame: Optional[FrameType] = None) -> None:
    """Print the debug message"""
    if not DEBUG:
        return
    if frame is not None:
        frameinfo = inspect.getframeinfo(frame)
        msg = (f'{msg} [In {frameinfo.function!r} at '
               f'{frameinfo.filename}:{frameinfo.lineno}]')
    sys.stderr.write(f'[{__name__}] DEBUG: {msg}\n')

def _get_frame(
        caller: int,
        ignore: Optional[
            List[Union[ModuleType, Tuple[ModuleType, str]]]
        ] = None
) -> FrameType:
    """This function makes sure that we get the desired frame,
    by caller and ignroe.

    The caller is the desired stack we want after excluding the frames we want
    to ignore. By default, this module (varname) and the builtin modules will
    be ignored.

    The frame_index defaults to 1 to exclude the calls from inside this module.
    """
    # Use loop instead of recursion to avoid creating additional stacks
    try:
        # We are at least skipping 2 frames:
        # one is this function, the other is any varname API that uses this
        # Don't bother to test them, just simply skip.
        frame_index = 2

        while caller > 0:
            frame = sys._getframe(frame_index)
            # loot at next frame anyway at next iteration
            frame_index += 1
            module = inspect.getmodule(frame)
            # exect = executing.Source.executing(frame)

            if module is sys.modules[__name__]:
                _debug('Skipping frame from varname', frame)
                continue

            if module and module.__name__ in sys.builtin_module_names:
                # havn't find a way to compose a test for this, skip for now
                _debug('Skipping builtin module', frame) # pragma: no cover
                continue # pragma: no cover

            if ignore and (
                    module in ignore or (
                        module,
                        executing.Source.for_frame(frame).
                        code_qualname(frame.f_code)
                    ) in ignore
            ):
                _debug('Ignored', frame)
                continue

            if ignore and module and '.' in module.__name__:
                # if asyncio specified, asyncio.runners, asyncio.events, etc
                # should be all ignored
                modnames = module.__name__.split('.')[:-1]
                if any(sys.modules['.'.join(modnames[:i+1])] in ignore
                       for i, _ in enumerate(modnames)):

                    _debug('Ignored', frame)
                    continue

            caller -= 1

            if caller > 0:
                _debug(f'Skipping ({caller - 1} more to skip)', frame)
            else:
                _debug('Gotcha!', frame)
                return frame

    except Exception as exc:
        raise VarnameRetrievingError from exc

def _get_node(
        caller: int,
        ignore: Optional[
            List[Union[ModuleType, Tuple[ModuleType, str]]]
        ] = None,
        raise_exc: bool = True
) -> Optional[ast.AST]:
    """Try to get node from the executing object.

    This can fail when a frame is failed to retrieve.
    One case should be when python code is executed in
    R pacakge `reticulate`, where only first frame is kept.

    When the node can not be retrieved, try to return the first statement.
    """
    try:
        frame = _get_frame(caller, ignore)
    except VarnameRetrievingError:
        return None

    exect = executing.Source.executing(frame)

    if exect.node:
        return exect.node

    if exect.source.text and exect.source.tree and raise_exc:
        raise VarnameRetrievingError(
            "Couldn't retrieve the call node. "
            "This may happen if you're using some other AST magic at the "
            "same time, such as pytest, ipython, macropy, or birdseye."
        )

    return None

def _lookfor_parent_assign(node: ast.AST) -> Optional[ast.Assign]:
    """Look for an ast.Assign node in the parents"""
    while hasattr(node, 'parent'):
        node = node.parent

        if isinstance(node, (ast.AnnAssign, ast.Assign)):
            return node
    return None

def _node_name(node: ast.AST) -> Optional[Union[str, Tuple[Union[str, tuple]]]]:
    """Get the node node name.

    Raises VarnameRetrievingError when failed
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, (ast.List, ast.Tuple)):
        return tuple(_node_name(elem) for elem in node.elts)

    raise VarnameRetrievingError(
        f"Can only get name of a variable or attribute, "
        f"not {ast.dump(node)}"
    )

def _bytecode_nameof(caller: int = 1) -> str:
    """Bytecode version of nameof as a fallback"""
    frame = _get_frame(caller)
    return _bytecode_nameof_cached(frame.f_code, frame.f_lasti)

@lru_cache()
def _bytecode_nameof_cached(code: CodeType, offset: int) -> str:
    """Cached Bytecode version of nameof

    We are trying this version only when the sourcecode is unavisible. In most
    cases, this will happen when user is trying to run a script in REPL/
    python shell, with `eval`, or other circumstances where the code is
    manipulated to run but sourcecode is not available.
    """
    instructions = list(dis.get_instructions(code))
    (current_instruction_index, current_instruction), = (
        (index, instruction)
        for index, instruction in enumerate(instructions)
        if instruction.offset == offset
    )

    if current_instruction.opname not in ("CALL_FUNCTION", "CALL_METHOD"):
        raise VarnameRetrievingError("Did you call nameof in a weird way?")

    name_instruction = instructions[
        current_instruction_index - 1
    ]

    if not name_instruction.opname.startswith("LOAD_"):
        raise VarnameRetrievingError("Argument must be a variable or attribute")

    name = name_instruction.argrepr
    if not name.isidentifier():
        raise VarnameRetrievingError(
            f"Found the variable name {name!r} which is obviously wrong. "
            "This may happen if you're using some other AST magic at the "
            "same time, such as pytest, ipython, macropy, or birdseye."
        )

    return name
