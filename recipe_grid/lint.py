"""
A collection of (fairly basic) linting functions for sanity checking recipes.

The following function will lint a (series of) :py:class:`Recipe` descriptions.

.. autofunction:: check

Linting errors are described by :py:class:`Lint` objects:

.. autoclass:: Lint
    :members:
    :undoc-members:

Different categories of linting errors are identified by members of the
following enumeration. Further details, however, are only given as
human-readable strings.

.. autoclass:: LintKind
    :members:
    :undoc-members:

"""

from typing import Iterable, Set, List, MutableMapping, Optional

from dataclasses import dataclass

from enum import Enum, auto

from math import isclose

from recipe_grid.units import UNIT_SYSTEM

from recipe_grid.recipe import (
    Recipe,
    SubRecipe,
    RecipeTreeNode,
    Reference,
    Step,
    Ingredient,
    Quantity,
    Proportion,
)


class LintKind(Enum):
    """Kinds of lint."""

    unused_ingredient = auto()
    sub_recipe_quantity_unknown = auto()
    sub_recipe_reference_incompatible_units = auto()
    sub_recipe_reference_non_positive_remainder = auto()
    sub_recipe_not_used_up = auto()
    sub_recipe_used_too_much = auto()


@dataclass(frozen=True)
class Lint:
    """
    A description a piece of lint found in a recipe.
    """

    kind: LintKind
    description: str


def check_for_unused_ingredients(recipe_blocks: Iterable[Recipe]) -> Iterable[Lint]:
    """
    Check for ingredients which are defined but never used.

    For example, in the following recipe::

        1 can of spam
        1 egg, boiled, shelled

        slice(spam, eggs)

    An ingredient 'egg' is defined but then later referenced as 'eggs'. This is
    almost certainly a mistake.

    One way to suppress this warning if you really did intend for an unused
    ingredient to remain listed is to explicitly give it a name, e.g.::

        1 can of spam
        egg = 1 egg, unused

        slice(spam)
    """

    implicit_ingredient_sub_recipes: Set[SubRecipe] = set()
    referenced_sub_recipes: Set[SubRecipe] = set()

    def visit_node(node: RecipeTreeNode) -> None:
        if isinstance(node, Reference):
            referenced_sub_recipes.add(node.sub_recipe)
            # Don't recurse into references
            return
        elif isinstance(node, SubRecipe):
            is_implicit_ingredient_sub_recipe = (
                len(node.output_names) == 1 and node.show_output_names is False
            )
            if is_implicit_ingredient_sub_recipe:
                implicit_ingredient_sub_recipes.add(node)

        for child_node in node.iter_children():
            visit_node(child_node)

    for recipe in recipe_blocks:
        for node in recipe.recipe_trees:
            visit_node(node)

    unused_ingredients = implicit_ingredient_sub_recipes - referenced_sub_recipes

    for unused_ingredient in sorted(
        unused_ingredients, key=lambda sr: str(sr.output_names[0])
    ):
        name = unused_ingredient.output_names[0]
        yield Lint(
            kind=LintKind.unused_ingredient,
            description=f"Ingredient '{name}' was defined but never used.",
        )


def check_sub_recipe_references_sum_to_whole(
    recipe_blocks: Iterable[Recipe],
) -> Iterable[Lint]:
    """
    Check that when a sub recipe used in several places is used completely.

    For example, in the following recipe::

        tomato sauce = 1 can of chopped tomatoes, boiled down

        pour over(
            cook(mix(1/2 of tomato sauce, chicken)),
            1/3 of tomato sauce,
        )

    The tomato sauce is not completely used up.
    """
    # NB: We don't capture (and therefore check) cases where a sub recipe
    # output is not used since this is probably intentional (e.g. a final or
    # discarded component of a recipe).
    #
    # sub_recipe_references[sub_recipe][output_index] = [Reference ...]
    sub_recipe_references: MutableMapping[
        SubRecipe, MutableMapping[int, List[Reference]]
    ] = {}

    def visit_node(node: RecipeTreeNode) -> None:
        if isinstance(node, Reference):
            sub_recipe_references.setdefault(node.sub_recipe, {})
            sub_recipe_references[node.sub_recipe].setdefault(node.output_index, [])
            sub_recipe_references[node.sub_recipe][node.output_index].append(node)
        else:
            for child_node in node.iter_children():
                visit_node(child_node)

    for recipe in recipe_blocks:
        for node in recipe.recipe_trees:
            visit_node(node)

    for sub_recipe, output_references in sub_recipe_references.items():
        for output_index, references in output_references.items():
            output_name = str(sub_recipe.output_names[output_index])
            # If this sub recipe contains a single ingredient, infer the quantity
            node = sub_recipe.sub_tree
            while isinstance(node, Step) and len(node.inputs) == 1:
                node = node.inputs[0]
            total_quantity: Optional[Quantity] = None
            if isinstance(node, Ingredient) and len(sub_recipe.output_names) == 1:
                total_quantity = node.quantity

            # Count up the quantities referred to in the references
            problem_encountered: bool = False
            used_proportion: float = 0.0
            for reference in references:
                if isinstance(reference.amount, Quantity):
                    if total_quantity is None:
                        problem_encountered = True
                        yield Lint(
                            kind=LintKind.sub_recipe_quantity_unknown,
                            description=(
                                f"A quantity "
                                f"({reference.amount.value} {reference.amount.unit}) "
                                f"of {output_name} was referenced but the total "
                                f"amount is not known so cannot be checked."
                            ),
                        )
                    else:
                        try:
                            if (
                                reference.amount.unit is not None
                                and total_quantity.unit is not None
                            ):
                                conversion = UNIT_SYSTEM.convert_between(
                                    reference.amount.unit.lower(),
                                    total_quantity.unit.lower(),
                                )
                            elif (
                                reference.amount.unit is None
                                and total_quantity.unit is None
                            ):
                                conversion = 1.0
                            else:
                                raise KeyError()
                            quantity_used = reference.amount.value * conversion
                            used_proportion += quantity_used / total_quantity.value
                        except KeyError:
                            problem_encountered = True
                            yield Lint(
                                kind=LintKind.sub_recipe_reference_incompatible_units,
                                description=(
                                    f"A reference to sub recipe {output_name} "
                                    f"is given using Incompatible units: "
                                    f"{reference.amount.unit}"
                                ),
                            )
                elif isinstance(reference.amount, Proportion):
                    if reference.amount.value is None:
                        if used_proportion >= 1.0:
                            problem_encountered = True
                            yield Lint(
                                kind=LintKind.sub_recipe_reference_non_positive_remainder,
                                description=(
                                    f"A reference to the remainder of recipe {output_name} "
                                    f"was made while none remains unused."
                                ),
                            )
                        used_proportion = max(1.0, used_proportion)
                    else:
                        used_proportion += reference.amount.value

            if not problem_encountered:
                perc = int(used_proportion * 100)
                if isclose(used_proportion, 1.0, rel_tol=0.02):
                    pass  # Used up (almost) exactly
                elif used_proportion < 1.0:
                    yield Lint(
                        kind=LintKind.sub_recipe_not_used_up,
                        description=(
                            f"Not all of {output_name} was used "
                            f"(about {100 - perc}% remains unused)."
                        ),
                    )
                else:  # used_proportion > 1.0
                    yield Lint(
                        kind=LintKind.sub_recipe_used_too_much,
                        description=(
                            f"More of {output_name} was used than is available "
                            f"(about {perc}% of the total amount used)."
                        ),
                    )


def check(recipe_blocks: Iterable[Recipe]) -> Iterable[Lint]:
    """
    Run all linting checks against a given recipe.
    """
    yield from check_for_unused_ingredients(recipe_blocks)
    yield from check_sub_recipe_references_sum_to_whole(recipe_blocks)
