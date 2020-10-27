"""
Recipes are rendered from their recipe data model descriptions
(:py:mod:`recipe_grid.recipe`) into tabular form for display.

Table rendering is split into two parts. First an abstract tabular description
is generated and then secondly this is rendered into its final form (i.e.
HTML). This decomposition should make it possible for future non-HTML output
formats to be supported.

The abstract table representation is defined in
:py:mod:`recipe_grid.renderer.table`, the recipe-to-table conversion in
:py:mod:`recipe_grid.renderer.recipe_to_table` and finally, table-to-HTML
conversion in :py:mod:`recipe_grid.renderer.html`

:py:mod:`recipe_grid.renderer.table`: Abstract table description
================================================================

.. automodule:: recipe_grid.renderer.table

:py:mod:`recipe_grid.renderer.recipe_to_table`: :py:class:`~recipe_grid.recipe.Recipe` to :py:class:`~recipe_grid.renderer.table.Table` transformation
======================================================================================================================================================

.. automodule:: recipe_grid.renderer.recipe_to_table

:py:mod:`recipe_grid.renderer.html`: HTML Table Renderer
========================================================

.. automodule:: recipe_grid.renderer.html

"""  # noqa: E501
