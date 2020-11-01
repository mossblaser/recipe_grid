.. _markdown_reference:

Markdown Recipe Syntax Reference
================================

Recipe Grid extends Markdown syntax to provide a convenient way of describing
recipes within a document. The `CommonMark <https://commonmark.org/>`_ Markdown
standard is supported with a small number of extensions described below.

Embedded recipes
----------------

Recipes descriptions should be embedded either in indented code blocks or
fenced codeblocks with ``recipe`` given as the 'info string'.  For example:

.. code:: md

    A Sample Markdown File
    ======================

    The following will be compiled as a recipe:

        fry(
            1 egg,
            1tsp oil,
        )

    So will:

    ```recipe
    fry(
        1 egg,
        1tsp oil,
    )
    ```

To create an ordinary code block, use a fenced block *without* ``recipe`` as
the info string.

Recipe descriptions may be split between several blocks with later blocks being
able to reference sub recipes in earlier blocks. For example:

.. code:: md

    Pizza
    =====

    First make pizza sauce:

        pizza sauce = boil down(tomatos, herbs)

    Next put it on a pizza:

        top(1 pizza base, pizza sauce, cheese)

If for some reason you wish to start a new recipe part way through your
document (and prevent sub recipes being inadvertently redefined), start this
new recipe with a fenced code block with ``new-recipe`` as the info string.


Scaleable values
----------------

In addition to embedding recipes within a Markdown document, it is also
possible to mark up numbers within the document which will be scaled along with
ingredient quantities when the recipe is scaled. This is achieved by enclosing
number-containing text within curly braces (``{`` and ``}``), as is supported
by the recipe description language. For example:

.. code:: md

    Burgers for 4
    =============

    Makes {4} delicious burgers, but can also be used to make {16} meat balls.

    ...

In the example above, the '4' and '16' in the opening paragraph will be scaled
with the recipe. For example, when the recipe is scaled to 50%, the paragraph
would be rewritten to contain '2 delicious burgers' and '8 meat balls'.

Numbers may be integers (e.g. ``123``), decimals (e.g. ``1.23``) or fractions
(e.g. ``4/3`` or ``1 1/3``). Other text within the curly braces will remain
unchanged.

To write a literal curly brace, use ``{\{}`` for an opening brace and ``{\}}``
for a closing brace.


Titles
------

If a Markdown document starts with a H1-level heading containing no special
formatting, the title of the document will be inferred from this.

When this heading ends with one of the following forms (where ``<N>`` is the
number of servings):

* ``to serve <N>``
* ``to make <N>``
* ``serves <N>``
* ``for <N>``
* ``makes <N>``
* ``serving <N>``

The title will be inferred to be whatever came before this and the recipe will
be assumed to be scaled to produce the specified number of servings.
