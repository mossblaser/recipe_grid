import pytest

from typing import List

from recipe_grid.markdown import compile_markdown

from recipe_grid.lint import (
    LintKind,
    Lint,
    check_for_unused_ingredients,
    check_sub_recipe_references_sum_to_whole,
)


class TestCheckForUnusedIngredients:
    @pytest.mark.parametrize(
        "recipe",
        [
            # Referenced but inlined ingredients
            "1 egg\nfry(egg)",
            "egg = 1 egg\nfry(egg)",
            "egg := 1 egg\nfry(egg)",
            # Referenced not inlined ingredients
            "2 eggs\nfry(1/2 of the eggs)\nboil(remaining eggs)",
            "eggs = 2 eggs\nfry(1/2 of the eggs)\nboil(remaining eggs)",
            "eggs := 2 eggs\nfry(1/2 of the eggs)\nboil(remaining eggs)",
            # Inline-defined ingredients
            "fry(1 egg, 2 cans of spam)",
            # Explicitly named, don't complain!
            "egg = 1 egg",
            "egg := 1 egg",
            # Custom units
            "{1 foobar} of egg\nfry(oil, egg)",
            # Quoted preposition
            "{1 foobar} 'of egg'\nfry(oil, of egg)",
        ],
    )
    def test_quiet_when_nothing_unused(self, recipe: str) -> None:
        markdown_recipe = compile_markdown(f"```recipe\n{recipe}\n```")
        recipe_blocks = markdown_recipe.recipes[0]
        assert list(check_for_unused_ingredients(recipe_blocks)) == []

    @pytest.mark.parametrize(
        "recipe, exp_description",
        [
            # Referenced by typo
            (
                "1 egg\nfry(eggs, oil)",
                "Ingredient 'egg' was defined but never used.",
            ),
            # Unknown unit means mismatch
            (
                "1 foobar of egg\nfry(egg, oil)",
                "Ingredient 'foobar of egg' was defined but never used.",
            ),
        ],
    )
    def test_finds_problems(self, recipe: str, exp_description: str) -> None:
        markdown_recipe = compile_markdown(f"```recipe\n{recipe}\n```")
        recipe_blocks = markdown_recipe.recipes[0]
        lint = list(check_for_unused_ingredients(recipe_blocks))
        assert len(lint) == 1
        assert lint[0].kind == LintKind.unused_ingredient
        assert lint[0].description == exp_description


class TestCheckSubRecipeReferencesSumToWhole:
    @pytest.mark.parametrize(
        "recipe",
        [
            # Sub recipe never referenced
            "1 egg, fried",
            "egg, shell = 1 egg, fried",
            # Multi-output sub recipe never referenced either
            "egg, shell = 1 egg, fried",
            # Implicit 100% use
            "egg, shell = 1 egg, fried\nchop(egg)",
            # Proportions only
            "1 egg\nfry(1/2 of egg)\nboil(1/2 of egg)",
            "1 egg\nfry(1/2 of egg)\nboil(1/4 of egg)\nscramble(1/4 of egg)",
            # Proportions only when no quantity given
            "egg\nfry(1/2 of egg)\nboil(1/2 of egg)",
            "egg\nfry(1/2 of egg)\nboil(1/4 of egg)\nscramble(1/4 of egg)",
            # Quantities only
            "1kg spam\nfry(0.5kg of spam)\nboil(0.5kg of spam)",
            "1kg spam\nfry(0.5kg of spam)\nboil(500g of spam)",
            # Proportions and quantities
            "1kg spam\nfry(1/2 of spam)\nboil(500g of spam)",
            # Remainder
            "1 egg\nfry(1/2 of egg)\nboil(remainder of egg)",
            "1kg spam\nfry(500g of spam)\nboil(remainder of spam)",
            # Some sub recipes used, others not
            "foo, bar, baz = 1 can spam, fried\ncook(bar)",
            "foo, bar, baz = 1 can spam, fried\ncook(1/2 of bar)\ndiscard(remaining bar)",
            # Approximate matching (e.g. where inexact units exist)
            "1kg spam\nfry(1oz of spam)\nboil(971.6g of spam)",
        ],
    )
    def test_quiet_when_everything_adds_up(self, recipe: str) -> None:
        markdown_recipe = compile_markdown(f"```recipe\n{recipe}\n```")
        recipe_blocks = markdown_recipe.recipes[0]
        assert list(check_sub_recipe_references_sum_to_whole(recipe_blocks)) == []

    @pytest.mark.parametrize(
        "recipe, exp_lint",
        [
            # Sub recipe with no quantity in ingredient has quantity unknown
            (
                "egg, fried\ndiscard(10g of egg)",
                {
                    Lint(
                        kind=LintKind.sub_recipe_quantity_unknown,
                        description=(
                            "A quantity (10 g) of egg was referenced but "
                            "the total amount is not known so cannot be checked."
                        ),
                    )
                },
            ),
            # Sub recipe with more than one ingredient has quantity unknown
            (
                "egg = fry(oil, 100g egg)\ndiscard(10g of egg)",
                {
                    Lint(
                        kind=LintKind.sub_recipe_quantity_unknown,
                        description=(
                            "A quantity (10 g) of egg was referenced but "
                            "the total amount is not known so cannot be checked."
                        ),
                    )
                },
            ),
            # Sub recipe with multiple outputs have quantity unknown (even if
            # defined)
            (
                "egg, shell = 100g egg, fried\ncrunch(10g of shell)",
                {
                    Lint(
                        kind=LintKind.sub_recipe_quantity_unknown,
                        description=(
                            "A quantity (10 g) of shell was referenced but "
                            "the total amount is not known so cannot be checked."
                        ),
                    )
                },
            ),
            # Incompatible units
            (
                "1kg of spam\nfry(1l of spam)",
                {
                    Lint(
                        kind=LintKind.sub_recipe_reference_incompatible_units,
                        description=(
                            "A reference to sub recipe spam is given "
                            "using Incompatible units: l"
                        ),
                    )
                },
            ),
            # Remainder when all used up
            (
                "1kg of spam\nfry(1kg of spam)\nboil(remaining spam)",
                {
                    Lint(
                        kind=LintKind.sub_recipe_reference_non_positive_remainder,
                        description=(
                            "A reference to the remainder of recipe spam was made "
                            "while none remains unused."
                        ),
                    )
                },
            ),
            # Remainder when more than used up
            (
                "1kg of spam\nfry(2kg of spam)\nboil(remaining spam)",
                {
                    Lint(
                        kind=LintKind.sub_recipe_reference_non_positive_remainder,
                        description=(
                            "A reference to the remainder of recipe spam was made "
                            "while none remains unused."
                        ),
                    )
                },
            ),
            # Sub recipe not used up completely
            (
                "1kg of spam\nfry(900g of spam)\nboil(50g of spam)",
                {
                    Lint(
                        kind=LintKind.sub_recipe_not_used_up,
                        description=(
                            "Not all of spam was used (about 5% remains unused)."
                        ),
                    )
                },
            ),
            # Sub recipe over-used
            (
                "1kg of spam\nfry(900g of spam)\nboil(500g of spam)",
                {
                    Lint(
                        kind=LintKind.sub_recipe_used_too_much,
                        description=(
                            "More of spam was used than is available "
                            "(about 140% of the total amount used)."
                        ),
                    )
                },
            ),
        ],
    )
    def test_finds_problems(self, recipe: str, exp_lint: List[Lint]) -> None:
        markdown_recipe = compile_markdown(f"```recipe\n{recipe}\n```")
        recipe_blocks = markdown_recipe.recipes[0]
        lint = list(check_sub_recipe_references_sum_to_whole(recipe_blocks))
        assert len(lint) == len(exp_lint)
        assert set(lint) == set(exp_lint)
