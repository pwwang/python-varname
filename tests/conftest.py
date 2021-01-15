import sys
import asyncio
import pytest
from varname import config

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
def enable_debug():
    config.debug = True
    yield
    config.debug = False

def run_async(coro):
    if sys.version_info < (3, 7):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    else:
        return asyncio.run(coro)
