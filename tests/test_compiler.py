import pytest

from typing import Optional

from textwrap import dedent

from fractions import Fraction

from recipe_grid.scaled_value_string import ScaledValueString as SVS

from recipe_grid.recipe import (
    Recipe,
    RecipeTreeNode,
    SubRecipe,
    Step,
    Ingredient,
    Reference,
    Proportion,
    Quantity,
)

from recipe_grid.compiler import (
    NameRedefinedError,
    ProportionGivenForIngredientError,
    infer_output_name,
    infer_quantity,
    normalise_output_name,
    compile,
)


def test_normalise_output_name() -> None:
    # Just a sanity check
    assert normalise_output_name(SVS(" Foo ")) == normalise_output_name(SVS("fOo"))
    assert normalise_output_name(SVS(" Foo ")) != normalise_output_name(SVS("bAr"))


@pytest.mark.parametrize(
    "recipe_tree, exp",
    [
        # Workable cases
        (Ingredient(SVS("spam")), SVS("spam")),
        (Step(SVS("fry"), (Ingredient(SVS("spam")),)), SVS("spam")),
        # Can't name step with several inputs
        (Step(SVS("fry"), (Ingredient(SVS("spam")), Ingredient(SVS("eggs")))), None),
        # Can't name references
        (Reference(SubRecipe(Ingredient(SVS("spam")), (SVS("spam"),)), 0), None),
        # Can't name sub recipes (they're already named!)
        (SubRecipe(Ingredient(SVS("spam")), (SVS("spam"),)), None),
    ],
)
def test_infer_output_name(recipe_tree: RecipeTreeNode, exp: Optional[SVS]) -> None:
    assert infer_output_name(recipe_tree) == exp


@pytest.mark.parametrize(
    "recipe_tree, exp",
    [
        # Workable cases
        (Ingredient(SVS("spam")), None),
        (Ingredient(SVS("spam"), Quantity(100)), Quantity(100)),
        (Ingredient(SVS("spam"), Quantity(100, "g")), Quantity(100, "g")),
        (Step(SVS("fry"), (Ingredient(SVS("spam"), Quantity(100)),)), Quantity(100)),
        (
            SubRecipe(Ingredient(SVS("spam"), Quantity(100)), (SVS("out"),)),
            Quantity(100),
        ),
        # Can't name step with several inputs
        (
            Step(
                SVS("fry"),
                (
                    Ingredient(SVS("spam"), Quantity(100)),
                    Ingredient(SVS("eggs"), Quantity(2)),
                ),
            ),
            None,
        ),
        # Can't name references
        (Reference(SubRecipe(Ingredient(SVS("spam")), (SVS("spam"),)), 0), None),
        # Can't work out sub recipe quantity when several outputs present
        (
            SubRecipe(Ingredient(SVS("spam"), Quantity(100)), (SVS("foo"), SVS("bar"))),
            None,
        ),
    ],
)
def test_infer_quantity(recipe_tree: RecipeTreeNode, exp: Optional[Quantity]) -> None:
    assert infer_quantity(recipe_tree) == exp


class TestRecipeCompiler:
    def test_ingredient_with_implied_output_name(self) -> None:
        assert compile(["spam"]) == [
            Recipe((SubRecipe(Ingredient(SVS("spam")), (SVS("spam"),), False),))
        ]

    @pytest.mark.parametrize("syntax", ["spam, fry", "fry(spam)"])
    def test_processed_ingredient_with_implied_output_name(self, syntax: str) -> None:
        assert compile([syntax]) == [
            Recipe(
                (
                    SubRecipe(
                        Step(SVS("fry"), (Ingredient(SVS("spam")),)),
                        (SVS("spam"),),
                        False,
                    ),
                )
            ),
        ]

    @pytest.mark.parametrize("output_name", ["spam", "foo"])
    def test_ingredient_with_explicit_output_name_always_shown(
        self, output_name: str
    ) -> None:
        # NB: output name always shown even if it matches what would be the inferred name
        assert compile([f"{output_name} = spam"]) == [
            Recipe((SubRecipe(Ingredient(SVS("spam")), (SVS(output_name),), True),))
        ]

    def test_multiple_outputs(self) -> None:
        assert compile(["foo, bar = spam"]) == [
            Recipe(
                (SubRecipe(Ingredient(SVS("spam")), (SVS("foo"), SVS("bar")), True),)
            )
        ]

    @pytest.mark.parametrize(
        "case, exp_error",
        [
            # Redefined (inconsistently)
            (
                "foo = spam\nfoo = eggs",
                """
                    At line 2 column 1:
                        foo = eggs
                        ^
                    The name foo has already been defined as a sub recipe.
                """,
            ),
            # Redefined (consistently)
            (
                "foo = spam\nfoo = spam",
                """
                    At line 2 column 1:
                        foo = spam
                        ^
                    The name foo has already been defined as a sub recipe.
                """,
            ),
            # Redefined within multiple outputs
            (
                "foo, foo = spam",
                """
                    At line 1 column 6:
                        foo, foo = spam
                             ^
                    The name foo has already been defined as a sub recipe.
                """,
            ),
            # Case-insensitive
            (
                "foo = spam\nFoO = eggs",
                """
                    At line 2 column 1:
                        FoO = eggs
                        ^
                    The name FoO has already been defined as a sub recipe.
                """,
            ),
        ],
    )
    def test_output_name_collision(self, case: str, exp_error: str) -> None:
        with pytest.raises(NameRedefinedError) as exc_info:
            compile([case])

        assert str(exc_info.value) == dedent(exp_error).strip()

    def test_string_compilation(self) -> None:
        # Just a sanity check
        assert compile(["spam {3 eggs}"]) == [
            Recipe(
                (
                    SubRecipe(
                        Ingredient(SVS(("spam ", 3, " eggs"))),
                        (SVS(["spam ", 3, " eggs"]),),
                        False,
                    ),
                )
            )
        ]

    def test_step_with_multiple_inputs_has_no_inferred_name(self) -> None:
        assert compile(["fry(spam, eggs)"]) == [
            Recipe(
                (Step(SVS("fry"), (Ingredient(SVS("spam")), Ingredient(SVS("eggs")))),)
            ),
        ]

    def test_reference_has_no_inferred_name(self) -> None:
        sub_recipe = SubRecipe(Ingredient(SVS("spam")), (SVS("spam"),), False)
        assert compile(["spam\nspam\nspam"]) == [
            Recipe((sub_recipe, Reference(sub_recipe, 0), Reference(sub_recipe, 0),)),
        ]

    def test_compilation_of_steps(self) -> None:
        assert compile(["fry(slice(spam), eggs)"]) == [
            Recipe(
                (
                    Step(
                        SVS("fry"),
                        (
                            Step(SVS("slice"), (Ingredient(SVS("spam")),)),
                            Ingredient(SVS("eggs")),
                        ),
                    ),
                )
            ),
        ]

    def test_reference_compilation(self) -> None:
        sub_recipe = SubRecipe(
            Step(SVS("open"), (Ingredient(SVS("spam")),)),
            (SVS("spam"), SVS("tin")),
            True,
        )
        assert compile(
            [
                "spam, tin = open(spam)\nspam\n1/3*spam\n25% * spam\nremaining spam\n2 tin\n50g spam"  # noqa: E501
            ]
        ) == [
            Recipe(
                (
                    sub_recipe,
                    Reference(sub_recipe, 0, Proportion(1.0)),
                    Reference(sub_recipe, 0, Proportion(Fraction(1, 3))),
                    Reference(sub_recipe, 0, Proportion(Fraction(1, 4))),
                    Reference(sub_recipe, 0, Proportion(None)),
                    Reference(sub_recipe, 1, Quantity(2)),
                    Reference(sub_recipe, 0, Quantity(50, "g")),
                )
            ),
        ]

    def test_ingredient_compilation(self) -> None:
        assert compile(["500g spam\n2 eggs\nheat"]) == [
            Recipe(
                (
                    # With unit
                    SubRecipe(
                        Ingredient(SVS("spam"), Quantity(500, "g")),
                        (SVS("spam"),),
                        False,
                    ),
                    # No unit
                    SubRecipe(
                        Ingredient(SVS("eggs"), Quantity(2)), (SVS("eggs"),), False,
                    ),
                    # No quantity
                    SubRecipe(Ingredient(SVS("heat")), (SVS("heat"),), False),
                )
            )
        ]

    def test_proportion_given_for_ingredient(self) -> None:
        with pytest.raises(ProportionGivenForIngredientError) as exc_info:
            compile(["1/2 * spam"])
        assert (
            str(exc_info.value)
            == dedent(
                """
                At line 1 column 1:
                    1/2 * spam
                    ^
                A proportion was given (implying a sub recipe is being referenced) but no sub recipe named spam exists.
            """  # noqa: E501
            ).strip()
        )

    @pytest.mark.parametrize(
        "quantity_spec", ["", "10g", "100%", "1.0 *", "remainder of"]
    )
    def test_inlining_single_references(self, quantity_spec: str) -> None:
        assert compile(
            [f"meat = 10g spam, sliced\nfry({quantity_spec} meat, eggs)"]
        ) == [
            Recipe(
                (
                    Step(
                        SVS("fry"),
                        (
                            Step(
                                SVS("sliced"),
                                (Ingredient(SVS("spam"), Quantity(10, "g")),),
                            ),
                            Ingredient(SVS("eggs")),
                        ),
                    ),
                )
            )
        ]

    def test_inlining_single_references_name_explicitly_required(self) -> None:
        assert compile(["meat := spam, sliced\nfry(meat, eggs)"]) == [
            Recipe(
                (
                    Step(
                        SVS("fry"),
                        (
                            SubRecipe(
                                Step(SVS("sliced"), (Ingredient(SVS("spam")),)),
                                (SVS("meat"),),
                            ),
                            Ingredient(SVS("eggs")),
                        ),
                    ),
                )
            )
        ]

    def test_dont_inline_multi_output_subrecipes(self) -> None:
        sub_recipe = SubRecipe(
            Ingredient(SVS("spam")), (SVS("meat"), SVS("tin")), True,
        )
        assert compile(["meat, tin = spam\nfry(meat, eggs)"]) == [
            Recipe(
                (
                    sub_recipe,
                    Step(
                        SVS("fry"),
                        (Reference(sub_recipe, 0), Ingredient(SVS("eggs")),),
                    ),
                )
            )
        ]

    def test_dont_inline_partial_uses_of_a_subrecipe(self) -> None:
        sub_recipe = SubRecipe(
            Ingredient(SVS("spam"), Quantity(100, "g")), (SVS("spam"),), False,
        )
        assert compile(["100g spam\nfry(50g spam, eggs)"]) == [
            Recipe(
                (
                    sub_recipe,
                    Step(
                        SVS("fry"),
                        (
                            Reference(sub_recipe, 0, Quantity(50, "g")),
                            Ingredient(SVS("eggs")),
                        ),
                    ),
                )
            )
        ]

    def test_dont_inline_definitions_from_earlier_blocks(self) -> None:
        sub_recipe = SubRecipe(
            Ingredient(SVS("spam"), Quantity(100, "g")), (SVS("spam"),), False,
        )
        recipe0 = Recipe((sub_recipe,))
        recipe1 = Recipe(
            (
                Step(
                    SVS("fry"),
                    (
                        Reference(sub_recipe, 0, Quantity(50, "g")),
                        Ingredient(SVS("eggs")),
                    ),
                ),
            ),
            follows=recipe0,
        )
        assert compile(["100g spam", "fry(50g spam, eggs)"]) == [recipe0, recipe1]