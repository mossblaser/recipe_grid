"""
This module provides renderers for markdown documents containing recipe
listings within code blocks.

Markdown syntax
===============

Recipes may be formatted as in the example below::

    Fried spam for 2
    ================

    An *unpleasant* yet inexpensive meal.

        1 can of spam, diced
        1 tsp of oil

        fry(oil, spam)

In the above example, the markdown document will be rendered into HTML as usual
but the listing within the indented code block will be compiled as a recipe.
Different parts of a recipe may be listed in separate code blocks and will be
compiled as part of the same recipe, with parts described in each block
rendered in that part of the document. For example::

    Pasta in tomato sauce for 1
    ===========================

    First make the pasta:

        75g of pasta
        cooked pasta = boil for 10 minutes(water, pasta)

    Then make the tomato sauce:

        1can chopped tomatoes
        1tsp mixed herbs

        sauce = boil down(chopped tomatoes, mixed herbs)

    And finally serve:

        serve(sauce, cooked pasta)

Fenced code blocks be used instead of indented code blocks. In this case, the
fence must be annotated with either ``recipe`` or ``new-recipe``, otherwise the
code block will be treated as an ordinary code block. For example:

    Spam again
    ==========

    Its not good.

    ```recipe
    1 can of spam, sliced
    ```

API
===

This module provides two main functions for compiling recipe-containing
markdown documents or just extracting the recipe sources from them:

.. autofunction:: render_markdown

.. autofunction:: extract_recipe_sources_from_markdown


Internals
=========

Internally the :py:mod:`marko` markdown parser is used providing support for
`CommonMark <https://commonmark.org/>`_ markdown syntax. An extension, mostly
defined in :py:mod:`recipe_grid.markdown.common`, serves to find
recipe-containing code blocks.
"""


from recipe_grid.markdown.html import render_markdown
from recipe_grid.markdown.extract import extract_recipe_sources_from_markdown
