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
    Quantity,
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

    def test_scale(self) -> None:
        step = Step(
            SVS(["fry in ", 4, " blocks"]), (Ingredient(SVS("spam"), Quantity(2)),)
        )

        assert step.scale(3) == Step(
            SVS(["fry in ", 12, " blocks"]),
            (Ingredient(SVS("spam"), Quantity(6)),),
        )


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

    def test_scale(self) -> None:
        sr_2 = SubRecipe(
            Ingredient(SVS("spam"), Quantity(2)), (SVS([2, " blocks of spam"]),)
        )
        sr_6 = SubRecipe(
            Ingredient(SVS("spam"), Quantity(6)), (SVS([6, " blocks of spam"]),)
        )

        assert Reference(sr_2, 0).scale(3) == Reference(sr_6, 0)
        assert Reference(sr_2, 0, Quantity(100, "g")).scale(3) == Reference(
            sr_6,
            0,
            Quantity(300, "g"),
        )


class TestQuantity:
    @pytest.mark.parametrize(
        "a, b, exp",
        [
            # Unitless
            (Quantity(1), Quantity(1), True),
            (Quantity(1), Quantity(2), False),
            (Quantity(1), Quantity(1, "g"), False),
            (Quantity(1, "g"), Quantity(1), False),
            # Same unit
            (Quantity(1, "g"), Quantity(1, "g"), True),
            (Quantity(1, "g"), Quantity(1, "G"), True),
            (Quantity(1, "g"), Quantity(2, "g"), False),
            (Quantity(1, "g"), Quantity(1, "kg"), False),
            # Unit conversion used
            (Quantity(1, "pounds"), Quantity(16, "ounces"), True),
            (Quantity(1, "pounds"), Quantity(17, "ounces"), False),
            # Incompatible, but valid units
            (Quantity(1, "kg"), Quantity(1, "l"), False),
            # Compatible but unknown units
            (Quantity(123, "foo"), Quantity(123, "foo"), True),
            (Quantity(123, "FOO"), Quantity(123, "foo"), True),
            # Floating point errors mean an approximate comparison is required
            # here
            (Quantity(10, "g"), Quantity(0.01, "kg"), True),
        ],
    )
    def test_has_equal_value_to(self, a: Quantity, b: Quantity, exp: bool) -> None:
        assert a.has_equal_value_to(b) is exp

    def test_scale(self) -> None:
        assert Quantity(123, "foo").scale(10) == Quantity(1230, "foo")


class TestProportion:
    def test_default_percentage_flag(self) -> None:
        assert Proportion(None).percentage is None
        assert Proportion(0.5).percentage is False
        assert Proportion(0.5, percentage=True).percentage is True

    def test_default_remainder_wording(self) -> None:
        assert Proportion(None).remainder_wording == "remaining"
        assert Proportion(None, remainder_wording="rest").remainder_wording == "rest"
        assert Proportion(0.5).remainder_wording is None

    def test_scale(self) -> None:
        assert Proportion(None).scale(10) == Proportion(None)
        assert Proportion(123).scale(10) == Proportion(123)


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

    def test_scale(self) -> None:
        sr_2 = SubRecipe(Ingredient(SVS("spam"), Quantity(2)), (SVS([2, "spams"]),))
        sr_6 = SubRecipe(Ingredient(SVS("spam"), Quantity(6)), (SVS([6, "spams"]),))

        assert sr_2.scale(3) == sr_6


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

    def test_scale(self) -> None:
        sr_2 = SubRecipe(Ingredient(SVS("spam"), Quantity(2)), (SVS("spam"),))
        ref_sr_2 = Reference(sr_2)

        sr_6 = SubRecipe(Ingredient(SVS("spam"), Quantity(6)), (SVS("spam"),))
        ref_sr_6 = Reference(sr_6)

        first_rec_2 = Recipe((sr_2,))
        second_rec_2 = Recipe((ref_sr_2,), follows=first_rec_2)

        first_rec_6 = Recipe((sr_6,))
        second_rec_6 = Recipe((ref_sr_6,), follows=first_rec_6)

        assert first_rec_2.scale(3) == first_rec_6
        assert second_rec_2.scale(3) == second_rec_6
