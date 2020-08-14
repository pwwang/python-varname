

.. image:: logo.png
   :target: logo.png
   :alt: python-varname


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
 <https://app.codacy.com/manual/pwwang/python-varname/dashboard>`_ `
.. image:: https://img.shields.io/gitter/room/pwwang/python-varname?style=flat-square
   :target: https://img.shields.io/gitter/room/pwwang/python-varname?style=flat-square
   :alt: Chat on gitter
 <https://gitter.im/python-varname/community>`_

Dark magics about variable names in python

`Change Log <https://pwwang.github.io/python-varname/CHANGELOG/>`_ | `API <https://pwwang.github.io/python-varname/api/varname/>`_

Installation
------------

.. code-block:: shell

   pip install python-varname

Features
--------


* Fetching variable names from inside the function/class call using ``varname``
* Fetching variable names directly using ``nameof``
* A value wrapper to store the variable name that a value is assigned to using ``Wrapper``
* Detecting next immediate attribute name using ``will``
* Shortcut for ``collections.namedtuple``
* Injecting ``__varname__`` to objects

Credits
-------

Thanks goes to these awesome people/projects:


.. raw:: html

   <table>
     <tr>
       <td align="center" style="min-width: 75px">
         <a href="https://github.com/alexmojaki">
           <img src="https://avatars0.githubusercontent.com/u/3627481?s=400&v=4" width="50px;" alt=""/>
           <br /><sub><b>@alexmojaki</b></sub>
         </a>
       </td>
       <td align="center" style="min-width: 75px">
         <a href="https://github.com/alexmojaki/executing">
           <img src="https://via.placeholder.com/50?text=executing" width="50px;" alt=""/>
           <br /><sub><b>executing</b></sub>
         </a>
       </td>
     </tr>
   </table>


Usage
-----

Retrieving the variable names from inside a function call/class instantiation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


* 
  From insdie a function call

  .. code-block:: python

       from varname import varname
       def function():
           return varname()

       func = function()
       # func == 'func'

* 
  ``varname`` calls being buried deeply

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

* 
  Retrieving instance name of a class

  .. code-block:: python

       class Klass:
           def __init__(self):
               self.id = varname()

           def copy(self):
               # also able to fetch inside a member call
               return varname()

       k = Klass()
       # k.id == 'k'

       k2 = k.copy()
       # k2 == 'k2'

* 
  Some unusual use

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
       # since you may not want func1 to be 'func'

       x = func(y = func())
       # x == 'x'

       # get part of the name
       func_abc = function()[-3:]
       # func_abc == 'abc'

       # function alias supported now
       function2 = function
       func = function2()
       # func == 'func'

       a = lambda: 0
       a.b = function()
       # a.b == 'b'

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

       a = {}
       a['b'] = get_name() # None

Value wrapper
^^^^^^^^^^^^^

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

Getting variable names directly
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Detecting next immediate attribute name
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
   awesome.do() # AttributeError: You don't have permission to do
   awesome.permit() # AttributeError: Should do something with AwesomeClass object
   awesome.permit().do() == 'I am doing!'

Shortcut for ``collections.namedtuple``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # instead of
   from collections import namedtuple
   Name = namedtuple('Name', ['first', 'last'])

   # we can do:
   from varname import namedtuple
   Name = namedtuple(['first', 'last'])

Injecting ``__varname__``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from varname import inject

   class MyList(list):
       pass

   a = inject(MyList())
   b = inject(MyList())

   a.__varname__ == 'a'
   b.__varname__ == 'b'

   a == b

   # other methods not affected
   a.append(1)
   b.append(1)
   a == b

Limitations
-----------

``python-varname`` is all depending on ``executing`` package to look for the node.
It does not work with any environment where ``executing`` is not able to detect the node.
For example:


* 
  Environments where other AST magics apply. For example: ``pytest``\ , ``ipython``\ , ``macropy``\ , or ``birdseye``.
  This will not work with ``pytest``\ :

  .. code-block:: python

     a = 1
     assert nameof(a) == 'a'

     # do this instead
     name_a = nameof(a)
     assert name_a == 'a'

* ``R`` with ``reticulate``.
