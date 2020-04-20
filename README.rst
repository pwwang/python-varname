.. role:: raw-html-m2r(raw)
   :format: html


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
   # func == func1 == 'func1'
   # a warning will be printed

   x = func(
       y = func()
   )
   # x == 'x'

   # This is heresy
   func_abc = function()[-3:]
   # func_abc == 'abc'

   # function alias supported now
   function2 = function
   func = function2()
   # func == 'func'

Limitations
-----------


* Not working in ``REPL``
* :raw-html-m2r:`<del>Calls have to be written in desired format</del>` (they don't have to since ``v0.1.0``\ )
* :raw-html-m2r:`<del>Context has to be estimated in advance, especially for functions with long argument list</del>` (it doesn't have to since ``v0.1.0``\ )
* You have to know at which stack the function/class will be called
* For performance, since inspection is involved, better cache the name
* 
  :raw-html-m2r:`<del>Aliases are not supported</del>` (supported since ``v0.1.0``\ )

  .. code-block:: diff

     - def function():
     -   return varname()
     - func = function

     - x = func() # unable to detect

* 
  :raw-html-m2r:`<del>False positives</del>` (Able to detect since ``v0.1.0``\ )

  .. code-block:: diff

     - def func(**kwargs):
     -     return varname()
     - x = func(
     -     y = func()
     - )
     - # x == 'y'

     - # to avoid this, you have to write the kwargs
     - # in the same line where the is called
     - x = func(y=func())
     - # x == 'x'
