"""Get the variable name that assigned by function/class calls"""
import re
import inspect

__version__ = "0.0.1"

VARNAME_INDEX = -1

def varname(context = 20, caller = 1):
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
	# where the function/class is called
	caller   = stacks[caller + 1]
	# if I called in a class' __init__?
	function = stack_me.function
	# find the class name
	if function == '__init__':
		function = stack_me.frame.f_locals['self'].__class__.__name__

	for i in reversed(range(caller.index + 1)):
		line = caller.code_context[i]

		if '=' not in line or function not in line:
			# it not something like 'a = func()'
			continue
		match = re.search(r'([\w_]+)\s*=\s*[\w_.]*' + function + r'\s*\(', line)
		if not match:
			break
		return match.group(1)
	VARNAME_INDEX += 1
	return 'var_{}'.format(VARNAME_INDEX)
