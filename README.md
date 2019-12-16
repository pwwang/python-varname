# python-varname

Retrieving variable names of function or class calls

## Installation
```shell
pip install python-varname
```

## Usage

### Retrieving the variable name inside a function

```python
from varname import varname
def function():
	return varname()

func = function()
# func == 'func'

# available calls to retrieve
func = function(
	# ...
)

func = \
	function()

# calls lead to failure of retrieving
func = function \
	()
func = [function()]
```

### Function with long argument list

```python
def function(*args):
	return varname()

func = function(
	1, # I
	2, # have
	3, # a
	4, # long
	5, # argument
	6, # list
)

# func == 'var_0'

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

# func == 'func'
```

### `varname` calls being buried deeply
```python
def function():
	# I know that at which stack this will be called
	return varname(caller = 3)

def function1():
	return function()

def function2():
	return function1()

func = function2()
# func == 'func'
```

### Retrieving instance name of a class object
```python
class Klass:
	def __init__(self):
		self.id = varname()
	def copy(self):
		return varname()

k = Klass()
# k.id == 'k'

k2 = k.copy()
# k2 == 'k2'
```

### `varname` calls being buried deeply for classes
```python
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
# k.id == 'k'

k2 = k.copy()
# k2 == 'k2'
```

### In case of failure to retrieve the name

`varname` has a static index starts from `0` to mark the variable name with failure.
```python
func = [function()]
# func == ['var_0']
func = function \
	()
# func == 'var_1'
```

## Limitations
- Calls have to be written in desired format
- Context have to be estimated in advance, especially for functions with long argument list
- You have to know at which stack the function/class will be called
- For performance, since inspection is involved, better cache the name
