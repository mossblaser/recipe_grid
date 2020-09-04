import pytest

from recipe_grid.scaled_value_string import ScaledValueString as SVS

from recipe_grid.recipe import (
    MultiOutputSubRecipeUsedAsNonRootNodeError,
    OutputIndexError,
    ZeroOutputSubRecipeError,
    ReferenceToInvalidSubRecipeError,
    Ingredient,
    Step,
    Reference,
    SubRecipe,
    Recipe,
)


class TestReference:
    def test_name_validation(self) -> None:
        sr = SubRecipe(Ingredient(SVS("spam")), [SVS("foo"), SVS("bar")])

        # Should work
        Reference(sr)
        Reference(sr, 0)
        Reference(sr, 1)

        # Unknown name
        with pytest.raises(OutputIndexError):
            Reference(sr, 2)


class TestSubRecipe:
    def test_child_assertion_checked(self) -> None:
        ingredient = Ingredient(SVS("spam"))
        singleton_sub_recipe = SubRecipe(Ingredient(SVS("eggs")), [SVS("foo")])
        multiple_sub_recipe = SubRecipe(
            Ingredient(SVS("foo")), [SVS("bar"), SVS("baz")]
        )

        # Should work
        SubRecipe(ingredient, [SVS("foo")])
        SubRecipe(singleton_sub_recipe, [SVS("foo")])

        # Cannot have child with multiple outputs
        with pytest.raises(MultiOutputSubRecipeUsedAsNonRootNodeError):
            SubRecipe(multiple_sub_recipe, [SVS("foo")])

    def test_at_least_one_output(self) -> None:
        with pytest.raises(ZeroOutputSubRecipeError):
            SubRecipe(Ingredient(SVS("spam")), [])


class TestRecipe:
    def test_reference_to_sub_recipe_not_in_recipe(self) -> None:
        external_sr = SubRecipe(Ingredient(SVS("eggs")), [SVS("foo")])
        ref = Reference(external_sr)

        with pytest.raises(ReferenceToInvalidSubRecipeError):
            Recipe([ref])

    def test_reference_to_sub_recipe_later_in_recipe(self) -> None:
        later_sr = SubRecipe(Ingredient(SVS("eggs")), [SVS("foo")])
        ref = Reference(later_sr)

        with pytest.raises(ReferenceToInvalidSubRecipeError):
            Recipe([ref, later_sr])

    def test_reference_to_nested_sub_recipe(self) -> None:
        nested_sr = SubRecipe(Ingredient(SVS("eggs")), [SVS("foo")])
        step = Step(SVS("scramble"), [nested_sr])

        ref = Reference(nested_sr)

        with pytest.raises(ReferenceToInvalidSubRecipeError):
            Recipe([step, ref])

    def test_nested_reference_to_sub_recipe_not_in_recipe(self) -> None:
        external_sr = SubRecipe(Ingredient(SVS("eggs")), [SVS("foo")])
        ref = Reference(external_sr)
        step = Step(SVS("bar"), [ref])

        with pytest.raises(ReferenceToInvalidSubRecipeError):
            Recipe([step])

    def test_valid_references(self) -> None:
        sr = SubRecipe(Ingredient(SVS("eggs")), [SVS("foo")])
        ref = Reference(sr)

        # Shouldn't fail
        Recipe([sr, ref])
