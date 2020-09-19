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
    Proportion,
    SubRecipe,
    Recipe,
)


class TestStep:
    def test_substitute(self) -> None:
        a = Ingredient(SVS("a"))
        b = Ingredient(SVS("b"))
        c = Ingredient(SVS("c"))
        d = Ingredient(SVS("d"))

        orig = Step(SVS("stir"), (a, b))

        assert orig.substitute(a, c) == Step(SVS("stir"), (c, b))
        assert orig.substitute(orig, c) == c
        assert orig.substitute(d, c) == orig


class TestReference:
    def test_name_validation(self) -> None:
        sr = SubRecipe(Ingredient(SVS("spam")), (SVS("foo"), SVS("bar")))

        # Should work
        Reference(sr)
        Reference(sr, 0)
        Reference(sr, 1)

        # Unknown name
        with pytest.raises(OutputIndexError):
            Reference(sr, 2)

    def test_substitute(self) -> None:
        a = Ingredient(SVS("a"))
        b = SubRecipe(a, (SVS("b"),))
        c = Ingredient(SVS("c"))
        d = SubRecipe(c, (SVS("d"),))

        orig = Reference(b, 0)

        assert orig.substitute(a, c) == Reference(SubRecipe(c, (SVS("b"),)), 0)
        assert orig.substitute(b, d) == Reference(SubRecipe(c, (SVS("d"),)), 0)
        assert orig.substitute(orig, c) == c


class TestProportion:
    def test_default_percentage_flag(self) -> None:
        assert Proportion(None).percentage is None
        assert Proportion(0.5).percentage is False
        assert Proportion(0.5, percentage=True).percentage is True

    def test_default_remainder_wording(self) -> None:
        assert Proportion(None).remainder_wording == "remaining"
        assert Proportion(None, remainder_wording="rest").remainder_wording == "rest"
        assert Proportion(0.5).remainder_wording is None


class TestSubRecipe:
    def test_child_assertion_checked(self) -> None:
        ingredient = Ingredient(SVS("spam"))
        singleton_sub_recipe = SubRecipe(Ingredient(SVS("eggs")), (SVS("foo"),))
        multiple_sub_recipe = SubRecipe(
            Ingredient(SVS("foo")), (SVS("bar"), SVS("baz"))
        )

        # Should work
        SubRecipe(ingredient, (SVS("foo"),))
        SubRecipe(singleton_sub_recipe, (SVS("foo"),))

        # Cannot have child with multiple outputs
        with pytest.raises(MultiOutputSubRecipeUsedAsNonRootNodeError):
            SubRecipe(multiple_sub_recipe, (SVS("foo"),))

    def test_at_least_one_output(self) -> None:
        with pytest.raises(ZeroOutputSubRecipeError):
            SubRecipe(Ingredient(SVS("spam")), ())

    def test_substitute(self) -> None:
        a = Ingredient(SVS("a"))
        b = Ingredient(SVS("b"))
        c = Ingredient(SVS("c"))

        orig = SubRecipe(a, (SVS("foo"),))

        assert orig.substitute(a, b) == SubRecipe(b, (SVS("foo"),))
        assert orig.substitute(orig, b) == b
        assert orig.substitute(c, b) == orig


class TestRecipe:
    def test_reference_to_sub_recipe_not_in_recipe(self) -> None:
        external_sr = SubRecipe(Ingredient(SVS("eggs")), (SVS("foo"),))
        ref = Reference(external_sr)

        with pytest.raises(ReferenceToInvalidSubRecipeError):
            Recipe((ref,))

    def test_reference_to_sub_recipe_later_in_recipe(self) -> None:
        later_sr = SubRecipe(Ingredient(SVS("eggs")), (SVS("foo"),))
        ref = Reference(later_sr)

        with pytest.raises(ReferenceToInvalidSubRecipeError):
            Recipe((ref, later_sr))

    def test_reference_to_nested_sub_recipe(self) -> None:
        nested_sr = SubRecipe(Ingredient(SVS("eggs")), (SVS("foo"),))
        step = Step(SVS("scramble"), (nested_sr,))

        ref = Reference(nested_sr)

        with pytest.raises(ReferenceToInvalidSubRecipeError):
            Recipe((step, ref))

    def test_nested_reference_to_sub_recipe_not_in_recipe(self) -> None:
        external_sr = SubRecipe(Ingredient(SVS("eggs")), (SVS("foo"),))
        ref = Reference(external_sr)
        step = Step(SVS("bar"), (ref,))

        with pytest.raises(ReferenceToInvalidSubRecipeError):
            Recipe((step,))

    def test_valid_references(self) -> None:
        sr = SubRecipe(Ingredient(SVS("eggs")), (SVS("foo"),))
        ref1 = Reference(sr)

        # Shouldn't fail
        rec1 = Recipe((sr, ref1))

        # Also shouldn't fail (since marked as follows)
        ref2 = Reference(sr)
        rec2 = Recipe((ref2,), follows=rec1)

        # Chained references
        ref3 = Reference(sr)
        Recipe((ref3,), follows=rec2)

        # Should fail: not referenced
        ref4 = Reference(sr)
        with pytest.raises(ReferenceToInvalidSubRecipeError):
            Recipe((ref4,))
