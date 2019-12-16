import pytest
from varname import varname

def test_function():

	def function():
		return varname()

	func = function()
	assert func == 'func'

	func = function(
	)
	assert func == 'func'

	func = \
		function()
	assert func == 'func'

	func = function\
		()
	assert func == 'var_0'

	func = [function()]
	assert func == ['var_1']

def test_function_context():

	def function(*args):
		return varname(context = 3)

	func = function(
		1, # I
		2, # have
		3, # a
		4, # long
		5, # argument
		6, # list
	)
	assert func == 'var_2'

	def function(*args):
		return varname(context = 20)

	func = function(
		1, # I
		2, # have
		3, # a
		4, # long
		5, # argument
		6, # list
	)
	assert func == 'func'

def test_function_deep():

	def function():
		# I know that at which stack this will be called
		return varname(caller = 3)

	def function1():
		return function()

	def function2():
		return function1()

	func = function2()
	assert func == 'func'

def test_class():

	class Klass:
		def __init__(self):
			self.id = varname()
		def copy(self):
			return varname()

	k = Klass()
	assert k.id == 'k'

	k2 = k.copy()
	assert k2 == 'k2'

def test_class_deep():

	class Klass:
		def __init__(self):
			self.id = self.some_internal()

		def some_internal(self):
			return varname(caller = 2)

		def copy(self):
			return self.copy_id()

		def copy_id(self):
			return self.copy_id_internal()

		def copy_id_internal(self):
			return varname(caller = 3)

	k = Klass()
	assert k.id == 'k'

	k2 = k.copy()
	assert k2 == 'k2'

