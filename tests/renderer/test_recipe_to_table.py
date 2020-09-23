from typing import Mapping, Tuple, List, cast

from recipe_grid.renderer.table import (
    Cell,
    Table,
    BorderType,
    combine_tables,
    set_border_around_table,
)

from recipe_grid.recipe import RecipeTreeNode, Ingredient, Reference, Step, SubRecipe

from recipe_grid.scaled_value_string import ScaledValueString as SVS

from recipe_grid.renderer.recipe_to_table import recipe_tree_to_table


def test_ingredient() -> None:
    ingredient = Ingredient(SVS("spam"))
    assert recipe_tree_to_table(ingredient) == set_border_around_table(
        Table.from_dict({(0, 0): Cell(ingredient)}), BorderType.sub_recipe
    )


def test_reference() -> None:
    sub_recipe = SubRecipe(Ingredient(SVS("spam")), (SVS("out"),))
    reference = Reference(sub_recipe, 0)
    assert recipe_tree_to_table(reference) == set_border_around_table(
        Table.from_dict({(0, 0): Cell(reference)}), BorderType.sub_recipe
    )


def test_step() -> None:
    input_0 = Ingredient(SVS("input 0"))
    input_1 = Ingredient(SVS("input 1"))

    input_2_ingredient = Ingredient(SVS("input 2"))
    input_2 = Step(SVS("chopped"), (input_2_ingredient,))
    step = Step(SVS("combine"), (input_0, input_1, input_2))

    assert recipe_tree_to_table(step) == set_border_around_table(
        Table.from_dict(
            cast(
                Mapping[Tuple[int, int], Cell[RecipeTreeNode]],
                {
                    (0, 0): Cell(input_0, columns=2),
                    (1, 0): Cell(input_1, columns=2),
                    (2, 0): Cell(input_2_ingredient),
                    (2, 1): Cell(input_2),
                    (0, 2): Cell(step, rows=3),
                },
            )
        ),
        BorderType.sub_recipe,
    )


def test_single_output_sub_recipe_shown() -> None:
    ingredient = Ingredient(SVS("spam"))
    step = Step(SVS("fry"), (ingredient,))
    sub_recipe = SubRecipe(step, (SVS("out"),))

    assert recipe_tree_to_table(sub_recipe) == set_border_around_table(
        Table.from_dict(
            cast(
                Mapping[Tuple[int, int], Cell[RecipeTreeNode]],
                {
                    (0, 0): Cell(sub_recipe, columns=2),
                    (1, 0): Cell(ingredient),
                    (1, 1): Cell(step),
                },
            )
        ),
        BorderType.sub_recipe,
    )


def test_single_output_sub_recipe_hidden() -> None:
    ingredient = Ingredient(SVS("spam"))
    step = Step(SVS("fry"), (ingredient,))
    sub_recipe = SubRecipe(step, (SVS("out"),), show_output_names=False)

    assert recipe_tree_to_table(sub_recipe) == set_border_around_table(
        Table.from_dict(
            cast(
                Mapping[Tuple[int, int], Cell[RecipeTreeNode]],
                {(0, 0): Cell(ingredient), (0, 1): Cell(step)},
            )
        ),
        BorderType.sub_recipe,
    )


def test_multiple_output_sub_recipe() -> None:
    ingredient_0 = Ingredient(SVS("spam"))
    ingredient_1 = Ingredient(SVS("eggs"))
    ingredient_2 = Ingredient(SVS("more spam"))
    step = Step(SVS("fry"), (ingredient_0, ingredient_1, ingredient_2))
    sub_recipe = SubRecipe(step, (SVS("output 0"), SVS("output 1")))

    assert recipe_tree_to_table(sub_recipe) == combine_tables(
        cast(
            List[Table[RecipeTreeNode]],
            [
                set_border_around_table(
                    Table.from_dict(
                        cast(
                            Mapping[Tuple[int, int], Cell[RecipeTreeNode]],
                            {
                                (0, 0): Cell(ingredient_0),
                                (1, 0): Cell(ingredient_1),
                                (2, 0): Cell(ingredient_2),
                                (0, 1): Cell(step, rows=3),
                            },
                        )
                    ),
                    BorderType.sub_recipe,
                ),
                Table.from_dict(
                    {
                        (0, 0): Cell(
                            sub_recipe,
                            rows=3,
                            border_top=BorderType.none,
                            border_right=BorderType.none,
                            border_bottom=BorderType.none,
                        )
                    }
                ),
            ],
        ),
        axis=1,
    )
