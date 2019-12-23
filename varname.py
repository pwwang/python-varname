"""Get the variable name that assigned by function/class calls"""
import re
import inspect
import logging

__version__ = "0.0.3"

VARNAME_INDEX = -1
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
if not LOGGER.handlers:
	_handler = logging.StreamHandler() # pylint: disable=invalid-name
	_handler.setFormatter(logging.Formatter('[%(asctime)s %(name)s] %(message)s'))
	LOGGER.addHandler(_handler)

def varname(context = 20, caller = 1, debug = False):
	"""Get the variable name
	@params:
		context (int): The max stacks to retrieve
		stack (int): Which stack that the function/class will be called
		lookback (int): How many lines should we look back for the call
	@returns:
		(str): The variable name
	"""
	global VARNAME_INDEX # pylint:disable=global-statement

	stacks = inspect.stack(context)[:(caller+2)]
	# where varname() is called
	stack_me = stacks[caller]
	if debug:
		LOGGER.info('- Handing case: %s: at line %s', stack_me.filename, stack_me.lineno)
		LOGGER.info('  (where varname() was called)')
	# where the function/class is called
	caller   = stacks[caller + 1]
	if debug:
		LOGGER.info('  Desired function/class was called in: %s: at line %s',
		caller.filename, caller.lineno)
	# if I called in a class' __init__?
	function = stack_me.function
	# find the class name
	if function == '__init__':
		function = stack_me.frame.f_locals['self'].__class__.__name__

	if debug:
		LOGGER.info('  Looking for where exactly %r was called ...', function)
		LOGGER.info('  Code context (index = %s):', caller.index)
		codelen = len(str(len(caller.code_context)))
		for i, code in enumerate(caller.code_context):
			LOGGER.info('  %s. %s', str(i).rjust(codelen), code.rstrip())
	for i in reversed(range(caller.index + 1)):
		line = caller.code_context[i]
		if debug:
			LOGGER.info('  Searching %d: %s', i, line.rstrip())
		if '=' not in line or function not in line:
			# it not something like 'a = func()'
			continue
		match = re.search(r'^\s*([\w_]+)\s*=\s*(?:\w+\.)*' + function + r'\s*(?:\(|$)', line)
		if not match:
			continue
		if debug:
			LOGGER.info('  Found at %r', line)
		return match.group(1)
	if debug:
		LOGGER.info('  Not found.')
	VARNAME_INDEX += 1
	return 'var_{}'.format(VARNAME_INDEX)
