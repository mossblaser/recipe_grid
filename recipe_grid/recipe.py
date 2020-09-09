"""
A data structure which defines a recipe.
"""


from typing import Union, Optional, Iterable, Tuple, Set

from fractions import Fraction

from dataclasses import dataclass, replace

from recipe_grid.scaled_value_string import ScaledValueString


class RecipeInvariantError(ValueError):
    """
    Base class for exceptions thrown when an invariant of the
    :py:class:`Recipe` data structure is violated.
    """


class MultiOutputSubRecipeUsedAsNonRootNodeError(RecipeInvariantError):
    """
    Thrown when a :py:class:`SubRecipe` with more than one named output is
    added as non-root node in a recipe tree.
    """


class OutputIndexError(RecipeInvariantError):
    """
    Thrown when a :py:class:`Reference` refers to output which does not exist
    in the referenced :py:class:`SubRecipe`.
    """


class ZeroOutputSubRecipeError(RecipeInvariantError):
    """
    Thrown if a :py:class:`SubRecipe` is defined with no named outputs.
    """


class ReferenceToInvalidSubRecipeError(RecipeInvariantError):
    """
    Thrown if a :py:class:`Reference` refers to a :py:class:`SubRecipe` node
    which is not a root node of a proceeding recipe tree in the same
    :py:class:`Recipe`.
    """


@dataclass(frozen=True)
class Quantity:
    """An absolute quantity."""

    value: Union[int, float, Fraction]
    """
    The quantity of this ingredient to be included. See also the
    :py:attr:`unit` field.
    """

    unit: Optional[str] = None
    """
    The name of the unit of measurement the :py:attr:`amount` field is given
    in. When None, a unit-less quantity is given (e.g. it is a count, e.g. 3
    apples).
    """

    # TODO: Implement unit-converting equality check(?)


@dataclass(frozen=True)
class Proportion:
    """A relative proportion."""

    value: Optional[Union[int, float, Fraction]] = None
    """
    The proportion (in the range 0.0 to 1.0) of a substance to be used. If
    None, this indicates whatever quantity remains.
    """


@dataclass(frozen=True)
class RecipeTreeNode:
    def _assert_can_be_child_node(self) -> None:
        """
        Throws a :py:class:`RecipeInvariantError` if adding this node as a
        child to another node would violate an invariant of the recipe data
        structure.
        """
        pass

    def iter_children(self) -> Iterable["RecipeTreeNode"]:
        """Iterate over the children of this node."""
        return iter(())

    def substitute(
        self, old: "RecipeTreeNode", new: "RecipeTreeNode"
    ) -> "RecipeTreeNode":
        """
        Return a copy of this recipe tree with the node ``old`` replaced with
        ``new``. (The old tree will remain intact).
        """
        if self == old:
            return new
        else:
            return self


@dataclass(frozen=True)
class Ingredient(RecipeTreeNode):
    """
    A leaf node in a tree describing an ingredient to be used.
    """

    description: ScaledValueString
    """A description of the ingredient."""

    quantity: Optional[Quantity] = None
    """
    The quantity of the ingredient, of specified. If None, the ingredient is
    quantity-less.
    """


@dataclass(frozen=True)
class Step(RecipeTreeNode):
    r"""
    A node in a tree where the node represents a step in a recipe (e.g. 'mix')
    and the children represent the inputs to that step.  Children may be other
    :py:class:`Step` instances, :py:class:`Ingredient` instances or
    :py:class:`Reference` instances referring to outputs of other
    :py:class:`SubRecipe`\ s.
    """

    description: ScaledValueString
    """A description of the step to be carried out."""

    inputs: Tuple[RecipeTreeNode, ...]
    """The inputs to (i.e. children) of this step."""

    def __post_init__(self) -> None:
        for node in self.inputs:
            node._assert_can_be_child_node()

    def iter_children(self) -> Iterable[RecipeTreeNode]:
        return iter(self.inputs)

    def substitute(self, old: RecipeTreeNode, new: RecipeTreeNode) -> RecipeTreeNode:
        if self == old:
            return new
        else:
            return replace(
                self, inputs=tuple(node.substitute(old, new) for node in self.inputs),
            )


@dataclass(frozen=True)
class Reference(RecipeTreeNode):
    """
    A reference to a named output of a :py:class:`SubRecipe`.
    """

    sub_recipe: "SubRecipe"
    output_index: int = 0
    """
    The :py:class:`SubRecipe` and output index being referenced. Only sub
    recipes which form the root of a recipe tree may be referenced.
    """

    amount: Union[Quantity, Proportion] = Proportion(1.0)
    """
    The amount of the referenced output to use. Default: all of it.
    """

    def __post_init__(self) -> None:
        if self.output_index >= len(self.sub_recipe.output_names):
            raise OutputIndexError(self.sub_recipe, self.output_index)

    def iter_children(self) -> Iterable[RecipeTreeNode]:
        yield self.sub_recipe


@dataclass(frozen=True)
class SubRecipe(RecipeTreeNode):
    """
    A sub recipe is a node representing a logical division in a recipe with
    some semantic significance.  For example, a pie recipe may divide the
    recipe into two sub recipes: one for the filling and another for the
    pastry.
    """

    sub_tree: RecipeTreeNode
    """The steps describing this sub-recipe."""

    output_names: Tuple[ScaledValueString, ...]
    """
    One or more names given to the outputs of this sub recipe.

    In the simple case there will be exactly one named output. In our pie
    recipe example, the sub recipe for the filling might have a single output
    named "Filling" and the pastry sub recipe might have one named "Pastry".

    For sub recipes which produce multiple outputs, names for these must be
    enumerated. For example, a sub recipe describing boiling some vegetables
    where both the vegetables and water will be used, two output names (e.g.
    "Boiled Vegetables" and "Vegetable Water" might be given).

    .. note::

        Sub recipes with a single output name may appear anywhere within a
        recipe tree. Where a SubRecipe is not at the root of a recipe it will
        typically be rendered inline but inset and labelled with the output
        name.

        Sub recipes with more than one named output may only be used as the
        root of a recipe tree.
    """

    show_output_names: bool = True
    """
    Specifies whether the output name(s) for this subrecipe should be rendered.
    For example when a sub-recipe consists of a single ingredient (e.g. '300g
    spam') with a single output (e.g. 'spam'), adding extra labelling would
    just be a distraction.
    """

    def __post_init__(self) -> None:
        self.sub_tree._assert_can_be_child_node()

        if len(self.output_names) == 0:
            raise ZeroOutputSubRecipeError()

    def _assert_can_be_child_node(self) -> None:
        if len(self.output_names) > 1:
            raise MultiOutputSubRecipeUsedAsNonRootNodeError()

    def substitute(self, old: RecipeTreeNode, new: RecipeTreeNode) -> RecipeTreeNode:
        if self == old:
            return new
        else:
            return replace(self, sub_tree=self.sub_tree.substitute(old, new),)


@dataclass(frozen=True)
class Recipe:
    """
    A recipe, defined in terms of a series of recipe trees. Later trees may
    reference the outputs of earlier trees resulting in a Directed Acyclic
    Graph (DAG) structure describing a recipe.
    """

    recipe_trees: Tuple[RecipeTreeNode, ...]

    follows: Optional["Recipe"] = None
    r"""
    If this recipe contains :py:class:`Reference`\ s to :py:class:`SubRecipe`\
    s in another :py:class:`Recipe`, this parameter should be set accordingly.
    (References are looked for recursively.
    """

    def __post_init__(self) -> None:
        # Check the consistency of all References (i.e. that they only refer to
        # SubRecipes which appear as roots of recipe trees prior to the tree
        # containing the Reference.
        previous_sub_recipe_roots: Set[SubRecipe] = set()

        next_recipe = self.follows
        while next_recipe is not None:
            previous_sub_recipe_roots.update(
                recipe_tree
                for recipe_tree in next_recipe.recipe_trees
                if isinstance(recipe_tree, SubRecipe)
            )
            next_recipe = next_recipe.follows

        for tree_root in self.recipe_trees:
            to_visit = [tree_root]
            while to_visit:
                node = to_visit.pop()
                if isinstance(node, Reference):
                    if node.sub_recipe not in previous_sub_recipe_roots:
                        raise ReferenceToInvalidSubRecipeError(node)
                to_visit.extend(node.iter_children())

            if isinstance(tree_root, SubRecipe):
                previous_sub_recipe_roots.add(tree_root)
