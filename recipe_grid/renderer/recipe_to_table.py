"""
A routine for converting a :py:mod:`recipe_grid.recipe` representation of a
recipe into a :py:class:`~Table`.
"""

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

    In the resulting :py:class:`~Table`, cell values are as follows. Firstly,
    the obvious cases:

    * :py:class:`~ingredient` is shown as is.
    * :py:class:`~Reference` is shown as its label.
    * :py:class:`~Step` is shown as its description.

    Finally, :py:class:`~SubRecipe`. These may appear in the table for one of
    two purposes:

    * For single-output sub recipes they should be rendered as a header row
      above the sub recipe cells containing the output name as text.
    * For multiple-output sub-recipes they should be placed in a cell to the
      right of the sub-recipe and contain (vertically arranged) all of the
      output names for the sub recipe.

    NB: The ``_root`` argument is for internal use and indicates if the node
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
