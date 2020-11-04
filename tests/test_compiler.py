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
            Recipe(
                (
                    sub_recipe,
                    Reference(sub_recipe, 0),
                    Reference(sub_recipe, 0),
                )
            ),
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
                "spam, tin = open(spam)\nspam\n1/3*spam\n25% of the spam\nleft over spam\n2 'tin'\n50g spam"  # noqa: E501
            ]
        ) == [
            Recipe(
                (
                    sub_recipe,
                    # spam
                    Reference(sub_recipe, 0, Proportion(1.0)),
                    # 1/3*spam
                    Reference(
                        sub_recipe, 0, Proportion(Fraction(1, 3), preposition="*")
                    ),
                    # 25% of the spam
                    Reference(
                        sub_recipe,
                        0,
                        Proportion(0.25, percentage=True, preposition="% of the"),
                    ),
                    # remaining
                    Reference(
                        sub_recipe, 0, Proportion(None, remainder_wording="left over")
                    ),
                    # 2 tin
                    Reference(sub_recipe, 1, Quantity(2.0)),
                    # 50g spam
                    Reference(sub_recipe, 0, Quantity(50.0, "g")),
                )
            ),
        ]

    def test_ingredient_compilation(self) -> None:
        assert compile(["500g spam\n2 eggs\n1 kg foo\n1 can of dog food\nheat"]) == [
            Recipe(
                (
                    # With unit
                    SubRecipe(
                        Ingredient(SVS("spam"), Quantity(500.0, "g")),
                        (SVS("spam"),),
                        False,
                    ),
                    # No unit
                    SubRecipe(
                        Ingredient(SVS("eggs"), Quantity(2.0)),
                        (SVS("eggs"),),
                        False,
                    ),
                    # With spacing between number and unit
                    SubRecipe(
                        Ingredient(
                            SVS("foo"), Quantity(1.0, "kg", value_unit_spacing=" ")
                        ),
                        (SVS("foo"),),
                        False,
                    ),
                    # With spacing between number and unit
                    SubRecipe(
                        Ingredient(
                            SVS("dog food"),
                            Quantity(
                                1,
                                "can",
                                value_unit_spacing=" ",
                                preposition=" of",
                            ),
                        ),
                        (SVS("dog food"),),
                        False,
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
        "quantity_spec", ["", "10g", "0.01 kg", "100%", "1.0 *", "remainder of"]
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
            Ingredient(SVS("spam")),
            (SVS("meat"), SVS("tin")),
            True,
        )
        assert compile(["meat, tin = spam\nfry(meat, eggs)"]) == [
            Recipe(
                (
                    sub_recipe,
                    Step(
                        SVS("fry"),
                        (
                            Reference(sub_recipe, 0),
                            Ingredient(SVS("eggs")),
                        ),
                    ),
                )
            )
        ]

    def test_dont_inline_partial_uses_of_a_subrecipe(self) -> None:
        sub_recipe = SubRecipe(
            Ingredient(SVS("spam"), Quantity(100, "g")),
            (SVS("spam"),),
            False,
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
            Ingredient(SVS("spam"), Quantity(100, "g")),
            (SVS("spam"),),
            False,
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

    def test_inlining_within_a_block(self) -> None:
        recipe0 = Recipe(
            (SubRecipe(Ingredient(SVS("egg")), (SVS("egg"),), show_output_names=False),)
        )
        recipe1 = Recipe(
            (Step(SVS("fry"), (Ingredient(SVS("spam"), Quantity(50, "g")),)),),
            follows=recipe0,
        )
        recipe2 = Recipe(
            (
                SubRecipe(
                    Ingredient(SVS("potato")), (SVS("potato"),), show_output_names=False
                ),
            ),
            follows=recipe1,
        )
        assert compile(["egg", "50g spam\nfry(spam)", "potato"]) == [
            recipe0,
            recipe1,
            recipe2,
        ]

    def test_inlines_within_inlines(self) -> None:
        recipe = Recipe(
            (
                Step(
                    SVS("boil"),
                    (
                        SubRecipe(
                            Step(
                                SVS("fry"),
                                (Ingredient(SVS("spam"), Quantity(100, "g")),),
                            ),
                            (SVS("fried spam"),),
                        ),
                        Ingredient(SVS("water")),
                    ),
                ),
            )
        )
        assert compile(
            ["100g spam\nfried spam := fry(spam)\nboil(fried spam, water)"]
        ) == [recipe]
