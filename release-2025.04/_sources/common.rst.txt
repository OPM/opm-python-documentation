OPM Common Python Documentation
===============================

Note on Import Paths
--------------------

In this documentation, some classes are referenced with their full import paths (e.g., opm.io.deck.DeckItem), while others are shown with just the class name. This distinction reflects how these classes are structured within the package:

- Fully Qualified Class Names: Classes displayed with their full import paths can be imported from their respective modules. They have constructors and can be directly instantiated in Python using the __init__ method. For example:
.. code-block:: python

    from opm.io.deck import DeckItem


- Unqualified Class Names: Classes displayed with just their names, e.g., Connection, do not have constructors in Python and cannot be directly instantiated in Python. Objects of these classes might be return values of methods of other classes.

Documentation
-------------

.. opm_common_docstrings::
