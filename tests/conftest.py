import sys
import importlib.util
import textwrap
import asyncio
from functools import wraps

from varname import core
# from varname.ignore import IgnoreList

import pytest
from varname import config, ignore


@pytest.fixture
def no_getframe():
    """
    Monkey-patch sys._getframe to fail,
    simulating environments that don't support varname
    """
    def getframe(_context):
        raise ValueError

    orig_getframe = sys._getframe
    try:
        sys._getframe = getframe
        yield
    finally:
        sys._getframe = orig_getframe


@pytest.fixture
def no_get_node_by_frame():
    """
    Monkey-patch sys._getframe to fail,
    simulating environments that don't support varname
    """
    def get_node_by_frame(frame):
        return None

    orig_get_node_by_frame = core.get_node_by_frame
    try:
        core.get_node_by_frame = get_node_by_frame
        yield
    finally:
        core.get_node_by_frame = orig_get_node_by_frame


@pytest.fixture
def no_pure_eval():
    sys.modules['pure_eval'] = None
    try:
        yield
    finally:
        del sys.modules['pure_eval']


@pytest.fixture
def enable_debug():
    config.debug = True
    try:
        yield
    finally:
        config.debug = False


@pytest.fixture
def frame_matches_module_by_ignore_id_false():
    orig_frame_matches_module_by_ignore_id = ignore.frame_matches_module_by_ignore_id
    ignore.frame_matches_module_by_ignore_id = lambda *args, **kargs: False
    try:
        yield
    finally:
        ignore.frame_matches_module_by_ignore_id = orig_frame_matches_module_by_ignore_id


def run_async(coro):
    if sys.version_info < (3, 7):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    else:
        return asyncio.run(coro)


def module_from_source(name, source, tmp_path):
    srcfile = tmp_path / f'{name}.py'
    lines = source.splitlines()
    start = 0
    while start < len(lines):
        if lines[start]:
            break
        start += 1
    lines = lines[start:]
    source = '\n'.join(lines)

    srcfile.write_text(textwrap.dedent(source))
    spec = importlib.util.spec_from_file_location(name, srcfile)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decor(func):
    """Decorator just for test purpose"""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def decor_wraps(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
