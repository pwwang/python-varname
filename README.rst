
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

Retrieving variable names of function or class calls

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
   # calls lead to failure of retrieving
   func = [function()]

Function with long argument list
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

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

``varname`` calls being buried deeply
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   def function():
       # I know that at which stack this will be called
       return varname(caller = 3)

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

In case of failure to retrieve the name
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``varname`` has a static index starts from ``0`` to mark the variable name with failure.

.. code-block:: python

   func = [function()]
   # func == ['var_0']
   func = function \
       ()
   # func == 'var_1'

Limitations
-----------


* Calls have to be written in desired format
* Context have to be estimated in advance, especially for functions with long argument list
* You have to know at which stack the function/class will be called
* For performance, since inspection is involved, better cache the name
* 
  Aliases are not supported

  .. code-block:: python

     def function():
       return varname()
     func = function

     x = func() # unable to detect

* 
  False positives

  .. code-block:: python

     def func(**kwargs):
         return varname()
     x = func(
         y = func()
     )
     # x == 'y'

     # to avoid this, you have to write the kwargs
     # in the same line where the is called
     x = func(y=func())
     # x == 'x'
