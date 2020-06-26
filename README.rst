
python-varname
==============

`
.. image:: https://img.shields.io/pypi/v/python-varname?style=flat-square
   :target: https://img.shields.io/pypi/v/python-varname?style=flat-square
   :alt: Pypi
 <https://pypi.org/project/python-varname/>`_ `
.. image:: https://img.shields.io/github/tag/pwwang/python-varname?style=flat-square
   :target: https://img.shields.io/github/tag/pwwang/python-varname?style=flat-square
   :alt: Github
 <https://github.com/pwwang/python-varname>`_ `
.. image:: https://img.shields.io/pypi/pyversions/python-varname?style=flat-square
   :target: https://img.shields.io/pypi/pyversions/python-varname?style=flat-square
   :alt: PythonVers
 <https://pypi.org/project/python-varname/>`_ `
.. image:: https://img.shields.io/travis/pwwang/python-varname?style=flat-square
   :target: https://img.shields.io/travis/pwwang/python-varname?style=flat-square
   :alt: Travis building
 <https://travis-ci.org/pwwang/python-varname>`_ `
.. image:: https://img.shields.io/codacy/grade/ed851ff47b194e3e9389b2a44d6f21da?style=flat-square
   :target: https://img.shields.io/codacy/grade/ed851ff47b194e3e9389b2a44d6f21da?style=flat-square
   :alt: Codacy
 <https://app.codacy.com/manual/pwwang/python-varname/dashboard>`_ `
.. image:: https://img.shields.io/codacy/coverage/ed851ff47b194e3e9389b2a44d6f21da?style=flat-square
   :target: https://img.shields.io/codacy/coverage/ed851ff47b194e3e9389b2a44d6f21da?style=flat-square
   :alt: Codacy coverage
 <https://app.codacy.com/manual/pwwang/python-varname/dashboard>`_

Dark magics about variable names in python

Installation
------------

.. code-block:: shell

   pip install python-varname

Usage
-----

Retrieving the variable name inside a function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

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

   func = function \
       ()

   func = (function
           ())

``varname`` calls being buried deeply
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   def function():
       # I know that at which stack this will be called
       return varname(caller=3)

   def function1():
       return function()

   def function2():
       return function1()

   func = function2()
   # func == 'func'

Retrieving instance name of a class object
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   class Klass:
       def __init__(self):
           self.id = varname()
       def copy(self):
           return varname()

   k = Klass()
   # k.id == 'k'

   k2 = k.copy()
   # k2 == 'k2'

``varname`` calls being buried deeply for classes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   class Klass:
       def __init__(self):
           self.id = self.some_internal()

       def some_internal(self):
           return varname(caller=2)

       def copy(self):
           return self.copy_id()

       def copy_id(self):
           return self.copy_id_internal()

       def copy_id_internal(self):
           return varname(caller=3)

   k = Klass()
   # k.id == 'k'

   k2 = k.copy()
   # k2 == 'k2'

Some unusual use
----------------

.. code-block:: python

   func = [function()]
   # func == ['func']

   func = [function(), function()]
   # func == ['func', 'func']

   func = function(), function()
   # func = ('func', 'func')

   func = func1 = function()
   # func == func1 == 'func'
   # a warning will be printed

   x = func(
       y = func()
   )
   # x == 'x'

   # get part of the name
   func_abc = function()[-3:]
   # func_abc == 'abc'

   # function alias supported now
   function2 = function
   func = function2()
   # func == 'func'

   # Since v0.1.3
   # We can ask varname to raise exceptions
   # if it fails to detect the variable name

   from varname import VarnameRetrievingError
   def get_name():
       try:
           # if raise_exc is False
           # "var_<index>" will be returned
           return varname(raise_exc=True)
       except VarnameRetrieveingError:
           return None

   a.b = get_name() # None

A value wrapper (added in v0.1.1)
---------------------------------

.. code-block:: python

   from varname import Wrapper

   foo = Wrapper(True)
   # foo.name == 'foo'
   # foo.value == True
   bar = Wrapper(False)
   # bar.name == 'bar'
   # bar.value == False

   def values_to_dict(*args):
       return {val.name: val.value for val in args}

   mydict = values_to_dict(foo, bar)
   # {'foo': True, 'bar': False}

Getting variable names directly (added in v0.1.2)
-------------------------------------------------

.. code-block:: python

   from varname import varname, nameof

   a = 1
   aname = nameof(a)
   # aname == 'a

   b = 2
   aname, bname = nameof(a, b)
   # aname == 'a', bname == 'b'

   def func():
       return varname() + '_suffix'

   f = func()
   # f == 'f_suffix'
   fname = nameof(f)
   # fname == 'f'

Detecting next immediate attribute name (added in ``v0.1.4``\ )
-----------------------------------------------------------------

.. code-block:: python

   from varname import will
   class AwesomeClass:
       def __init__(self):
           self.will = None

       def permit(self):
           self.will = will()
           if self.will == 'do':
               # let self handle do
               return self
           raise AttributeError('Should do something with AwesomeClass object')

       def do(self):
           if self.will != 'do':
               raise AttributeError("You don't have permission to do")
           return 'I am doing!'

   awesome = AwesomeClass()
   awesome.do() # AttributeError: Should do something with AwesomeClass object
   awesome.permit() # AttributeError: You don't have permission to do
   awesome.permit().do() == 'I am doing!'

Shortcut for ``collections.namedtuple`` (addedin ``v0.1.6``\ )
--------------------------------------------------------------------

.. code-block:: python

   # instead of
   from collections import namedtuple
   Name = namedtuple('Name', ['first', 'last'])

   # we can do:
   from varname import namedtuple
   Name = namedtuple(['first', 'last'])

Limitations
-----------


* Working in ``ipython REPL`` but not in standard ``python console``
* You have to know at which stack the function/class will be called
* For performance, since inspection is involved, better cache the name
* ``nameof`` cannot be used in statements in ``pytest``
  .. code-block::

     a = 1
     assert nameof(a) == 'a'
     # Retrieving failure.
     # The right way:
     aname = nameof(a)
     assert aname == 'a'
