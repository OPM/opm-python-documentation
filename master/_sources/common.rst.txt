OPM Common Python Documentation
===============================

Note on Import Paths
--------------------

In this documentation, you may notice that some classes are referenced with their full import paths (e.g., opm.io.deck.DeckItem), while others are shown with just the class name. This distinction reflects how these classes are structured within the package:

- Fully Qualified Paths: Classes displayed with their full import paths can be directly imported from their respective modules. For example:
.. code-block:: python

    from opm.io.deck import DeckItem


- Simplified Class Names: Classes displayed with just their names, e.g. Connectoin, are intended for internal use or may require additional context when importing. Refer to the specific module documentation for the correct import path if needed.

This structure allows for a organized and modular package, helping to easily access commonly used classes while maintaining clarity for internal components.

Documentation
-------------

.. opm_common_docstrings::
