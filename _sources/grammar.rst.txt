.. _grammar:

Formal Recipe Description Language Grammar
==========================================

The following :py:mod:`peggie` PEG grammar formally defines the Recipe Grid
recipe description language.

.. note::

    A still detailed, though less formal, description of the recipe description
    language is available in the :ref:`language_reference`.
    
    For a higher-level introduction, see the :ref:`tutorial`.

.. include:: ../../recipe_grid/parser/grammar.peg
    :literal:


In the grammar above, the string ``@KNOWN_UNITS@`` is substituted for a regular
expression which matches the following strings (with spaces here matching any
quantity of whitespace):

    .. rgunitlist::

.. note::

    The above grammar is not able to distinguish between references and
    ingredients and so is written as if only references exist. The Recipe Grid
    compiler resolves this distinction in a later compilation stage.
