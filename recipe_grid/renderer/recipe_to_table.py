"""
The following routine converts a single recipe tree
(:py:class:`~recipe_grid.recipe.RecipeTreeNode`) into the equivalent
:py:class:`~Table` form. It should be used to convert each recipe tree in
:py:attr:`Recipe.recipe_trees <recipe_grid.recipe.Recipe.recipe_trees>` into its own table in the
rendered output.

.. autofunction:: recipe_tree_to_table(recipe_tree: recipe_grid.recipe.RecipeTreeNode) -> recipe_grid.renderer.table.Table

"""  # noqa: E501

from typing import cast

from recipe_grid.recipe import (
    RecipeTreeNode,
    Ingredient,
    Reference,
    Step,
    SubRecipe,
)

from recipe_grid.renderer.table import (
    BorderType,
    Cell,
    Table,
    right_pad_table,
    combine_tables,
    set_border_around_table,
)


def recipe_tree_to_table(
    recipe_tree: RecipeTreeNode, _root: bool = True
) -> Table[RecipeTreeNode]:
    """
    Convert a recipe tree into tabular form.

    To display the resulting :py:class:`~Table`, cell contents should be
    rendered as indicated below.

    Firstly, the obvious cases:

    * :py:class:`~Ingredient` is shown as the ingredient quantity and name etc.
    * :py:class:`~Reference` is shown as its label (and quantity/proportion
      etc.)
    * :py:class:`~Step` is shown as its description. The cells immediately to
      the left in the generated table will contain the inputs to this step.

    Finally, cells containing a :py:class:`~SubRecipe` may appear in the table
    for one of two purposes:

    * For single-output sub recipes, the cell containing the
      :py:class:`SubRecipe` will be located above the cells containing the body
      of the sub recipe. This cell should be rendered in the style of a heading
      and containing the output name as the text.
    * For multiple-output sub recipes, thec cell containing the
      :py:class:`SubRecipe` will be immediately to the right of the cells
      defining the sub-recipe and should be rendered as a list all of the
      output names for the sub recipe, for example as a bulleted list.

      .. note::

          This cell will have all but its left border style set to be
          :py:attr:`BorderType.none` to give the appearance of the output list
          being located out to the right of the rest of the table.

    Unless otherwise stated, all cells will have all borders set to
    :py:attr:`BorderType.normal` with the exception of those borders of cells
    near the edges of a sub recipe block. These will have a style of
    :py:attr:`BorderType.sub_recipe`.

    .. note::

        The ``_root`` argument is for internal use and must be left unspecified
        when called by external users. Internally, it indicates if the node
        passed to this function is the root node of its recipe tree.
    """
    if isinstance(recipe_tree, (Ingredient, Reference)):
        table: Table[RecipeTreeNode] = Table([[Cell(recipe_tree)]])
        if _root:
            return set_border_around_table(table, BorderType.sub_recipe)
        else:
            return table

    elif isinstance(recipe_tree, Step):
        input_tables = [
            recipe_tree_to_table(input_tree, False) for input_tree in recipe_tree.inputs
        ]

        # Pad all input tables to same width and stack them up
        input_columns = max(table.columns for table in input_tables)
        input_tables = [right_pad_table(table, input_columns) for table in input_tables]
        combined_input_tables = combine_tables(input_tables, axis=0)

        # Add step to RHS of inputs
        table = combine_tables(
            [
                combined_input_tables,
                Table.from_dict(
                    {(0, 0): Cell(recipe_tree, rows=combined_input_tables.rows)}
                ),
            ],
            axis=1,
        )

        if _root:
            return set_border_around_table(table, BorderType.sub_recipe)
        else:
            return table
    elif isinstance(recipe_tree, SubRecipe):
        sub_tree_table = recipe_tree_to_table(recipe_tree.sub_tree, False)

        if len(recipe_tree.output_names) == 1:
            if recipe_tree.show_output_names:
                return set_border_around_table(
                    combine_tables(
                        [
                            Table.from_dict(
                                {
                                    (0, 0): Cell(
                                        cast(RecipeTreeNode, recipe_tree),
                                        columns=sub_tree_table.columns,
                                    ),
                                }
                            ),
                            sub_tree_table,
                        ],
                        axis=0,
                    ),
                    BorderType.sub_recipe,
                )
            else:
                return set_border_around_table(sub_tree_table, BorderType.sub_recipe)
        else:
            return combine_tables(
                [
                    set_border_around_table(sub_tree_table, BorderType.sub_recipe),
                    Table.from_dict(
                        {
                            (0, 0): Cell(
                                cast(RecipeTreeNode, recipe_tree),
                                rows=sub_tree_table.rows,
                                border_top=BorderType.none,
                                border_right=BorderType.none,
                                border_bottom=BorderType.none,
                            ),
                        }
                    ),
                ],
                axis=1,
            )
    else:
        raise NotImplementedError(type(recipe_tree))
