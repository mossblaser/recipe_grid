r"""
The :py:mod:`recipe_grid.recipe` module defines the Directed Acyclic Graph
(DAG) data structure used to describe recipes.


Overview
========

Recipes are defined as a series of trees, principally consisting of
:py:class:`Ingredient` nodes and :py:class:`Step` nodes.

An :py:class:`Ingredient` node contains a name and an optional quantity.

A :py:class:`Step` node contains a description of the step and a series of
input nodes (children).

A simple recipe might only consist of a single tree of :py:class:`Ingredient`
and :py:class:`Step` nodes. For example, here's how a simple pasta meal might
be represented.

.. graphviz::

   digraph foo {

      subgraph {
          node [shape=ellipse]

          onion [label=<Onion<br/>(Ingredient)>]
          tomatoes [label=<Chopped Tomatoes<br/>(Ingredient)>]
          pasta [label=<Pasta<br/>(Ingredient)>]
      }

      subgraph {
          node [shape=rectangle]

          chop [label=<Chop<br/>(Step)>]
          fry [label=<Fry<br/>(Step)>]
          boildown [label=<Boil down<br/>(Step)>]
          boil [label=<Boil<br/>(Step)>]
          mix [label=<Mix<br/>(Step)>]
      }

      chop -> onion;

      fry -> chop;

      boildown -> fry;
      boildown -> tomatoes;

      boil -> pasta;

      mix -> boildown;
      mix -> boil;
   }

Sometimes a sub tree within a recipe might be identified as its own sub recipe
and given an emphasising border and title in the rendered recipe table.  For
example, in the recipe above we might make the pasta sauce a sub recipe. To
represent this, a :py:class:`SubRecipe` node type is used which always has exactly one
child and one or more named outputs. In this example, there is only one output
('Pasta sauce').  We'll return to the case with multiple named outputs later.

.. graphviz::

   digraph foo {

      subgraph {
          node [shape=ellipse]

          onion [label=<Onion<br/>(Ingredient)>]
          tomatoes [label=<Chopped Tomatoes<br/>(Ingredient)>]
          pasta [label=<Pasta<br/>(Ingredient)>]
      }

      subgraph {
          node [shape=rectangle]

          chop [label=<Chop<br/>(Step)>]
          fry [label=<Fry<br/>(Step)>]
          boildown [label=<Boil down<br/>(Step)>]
          boil [label=<Boil<br/>(Step)>]
          mix [label=<Mix<br/>(Step)>]
      }

      subgraph {
          node [shape=Mrecord]

          sauce [label="{<fs>Pasta sauce|<fo>(SubRecipe)}"]
      }

      chop -> onion;

      fry -> chop;

      boildown -> fry;
      boildown -> tomatoes;

      sauce:fo -> boildown;

      boil -> pasta;

      mix -> sauce:fs:n;
      mix -> boil;
   }

In other cases, an ingredient or whole sub recipe may be split into parts and
used separately. In this case, a :py:class:`Reference` node may be used to
refer to a :py:class:`SubRecipe` which must be the root of a previous tree in the
recipe. For example, in the recipe below, a Sub Recipe for grated cheese is
referenced in two places, with 75% being mixed into the main recipe and 25%
being used to top it:

.. graphviz::

   digraph foo {

      subgraph {
          node [shape=ellipse]

          cheese [label=<Cheese<br/>(Ingredient)>]
          white_sauce [label=<White sauce<br/>(Ingredient)>]
          pasta [label=<Pasta<br/>(Ingredient)>]
      }

      subgraph {
          node [shape=rectangle]

          grate [label=<Grate<br/>(Step)>]
          mix [label=<Mix<br/>(Step)>]
          top [label=<Top<br/>(Step)>]
      }

      subgraph {
          node [shape=diamond]

          refm [label=<75%<br/>(Reference)>]
          reft [label=<25%<br/>(Reference)>]
      }

      subgraph {
          node [shape=Mrecord]

          grated_cheese [label="{<fc>Grated cheese|<fo>(SubRecipe)}"]
      }

      grate -> cheese;
      grated_cheese:fo -> grate;

      mix -> refm;
      mix -> white_sauce;
      mix -> pasta;

      top -> mix;
      top -> reft;

      subgraph {
            edge [constraint=false,style=dashed];

            refm:sw -> grated_cheese:fc:n
            reft:sw -> grated_cheese:fc:n
      }
   }

A final case is where a :py:class:`SubRecipe` has more than one output. This might occur
when, for example, when vegetables are boiled and both the vegetables and the
water are reserved and used in a later step. Each output may then be referenced
separately by :py:class:`Reference` nodes. :py:class:`SubRecipe` nodes with more than
one output must be the root of a recipe tree.

.. graphviz::

   digraph foo {
      subgraph {
          node [shape=ellipse]

          vegetables [label=<Vegetables<br/>(Ingredient)>]
          gravy_granules [label=<Gravy granules<br/>(Ingredient)>]
      }

      subgraph {
          node [shape=rectangle]

          boil [label=<Boil, reserving water<br/>(Step)>]
          make [label=<Make gravy<br/>(Step)>]
          pour [label=<Pour over<br/>(Step)>]
      }

      subgraph {
          node [shape=diamond]

          refv [label=<(Reference)>]
          refw [label=<(Reference)>]
      }

      subgraph {
          node [shape=Mrecord]

          boiled_veg [label="{{<fv>Boiled Vegetables|<fw>Water}|<fo>(SubRecipe)}"]
      }

      boil -> vegetables;
      boiled_veg -> boil;

      make -> gravy_granules;
      make -> refw;

      pour -> make;
      pour -> refv;

      subgraph {
          edge [constraint=false,style=dashed];

          refv:sw -> boiled_veg:fv:n
          refw:sw -> boiled_veg:fw:n
      }
   }


Data structures
===============

A Recipe is defined at its root by a :py:class:`Recipe` instance. In a simple
document there will be a single :py:class:`Recipe` instance which contains the
entire DAG for that recipe. For more complex documents where the recipe is
presented in several sections, each section of the recipe will be represented
by its own :py:class:`Recipe` with back-references to prior :py:class:`Recipe`\
s in :py:attr:`Recipe.follows`.

.. autoclass:: Recipe
    :members:

DAG Structure
-------------

Recipe trees are in turn defined using subclasses of
:py:class:`RecipeTreeNode`:

.. autoclass:: RecipeTreeNode
    :members:

.. autoclass:: Ingredient
    :members:

.. autoclass:: Step
    :members: description, inputs

.. autoclass:: SubRecipe
    :members: sub_tree, output_names, show_output_names

.. autoclass:: Reference
    :members: output_index, amount


Quantities and Proportions
--------------------------

Absolute quantities (for ingredients and references) and relative proportions
(for references only) are defined as follows:

.. autoclass:: Quantity

.. autoclass:: Proportion

Exceptions
----------

The DAG structure invariants are enforced by checks in their constructors and
any non-conforming input will produce a :py:exc:`RecipeInvariantError`
subclass.

.. autoexception:: RecipeInvariantError

.. autoexception:: MultiOutputSubRecipeUsedAsNonRootNodeError

.. autoexception:: OutputIndexError

.. autoexception:: ZeroOutputSubRecipeError

.. autoexception:: ReferenceToInvalidSubRecipeError

"""


from typing import cast, Union, Optional, Iterable, Tuple, Set

import math

from fractions import Fraction

from dataclasses import dataclass, replace

from recipe_grid.units import UNIT_SYSTEM

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
    """
    An absolute quantity.

    Suggested rendering::

        q.value
        + (q.value_unit_spacing + q.unit if q.unit is not None else "")
        + q.preposition
    """

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

    value_unit_spacing: str = ""
    """
    The whitespace to include between the value and unit when displayed, if
    any. If unit is omitted, this should be an empty string.
    """

    preposition: str = ""
    """
    A preposition to append after the value and unit, including any necessary
    leading whitespace. For example " of" for "50g of".
    """

    def has_equal_value_to(self, other: "Quantity") -> bool:
        """
        Compare two quantities, returning true if the quantities are equal (to
        within a small tolerance (allowing for float imprecision) and ignoring
        other metadata.
        """
        other_to_self_scale: Union[int, float, Fraction]
        if self.unit is None and other.unit is None:
            other_to_self_scale = 1
        elif self.unit is None or other.unit is None:
            # Comparison between unit and unitless quantities
            return False
        else:
            try:
                other_to_self_scale = UNIT_SYSTEM.convert_between(
                    other.unit.lower(),
                    self.unit.lower(),
                )
            except KeyError:  # No conversion available
                if self.unit.lower() == other.unit.lower():
                    other_to_self_scale = 1
                else:
                    return False

        return math.isclose(self.value, other.value * other_to_self_scale)

    def scale(self, factor: Union[int, float, Fraction]) -> "Quantity":
        return replace(self, value=self.value * factor)


@dataclass(frozen=True)
class Proportion:
    """
    A relative proportion.

    Suggested rendering::

        (
            (q.value * 100 if q.percentage else q.value)
            if q.value is None else
            q.remainder_wording
        )
        + q.preposition
    """

    value: Optional[Union[int, float, Fraction]] = None
    """
    The proportion (in the range 0.0 to 1.0) of a substance to be used. If
    None, this indicates whatever quantity remains.
    """

    percentage: Optional[bool] = None
    """
    If value is not None, a boolean indicating if the value should be rendered
    as a percentage (i.e. scaled up to the range 0 to 100).

    This field must be None iff value is None.

    If left as None but value is given, this field will be set to False
    automatically.
    """

    remainder_wording: Optional[str] = None
    """
    If value is None, the word to use to indicate "remainder", e.g.
    "remainder", "left over", etc.

    Must be None iff value is not None.

    If left as None but value is also None, this field will be set to
    "remaining" automatically.
    """

    preposition: str = ""
    """
    A preposition to append after the value, including any necessary
    leading whitespace. Examples:

    * "rest of the sauce" -> " of the"
    * "0.5 * sauce" -> " *"
    * "25% of the sauce" -> "% of the"

    Note that for percentages, the preposition string is responsible for
    indicating to a reader that the value is a percentage (e.g. it should
    include a '%' symbol).
    """

    def __post_init__(self) -> None:
        if self.value is not None and self.percentage is None:
            object.__setattr__(self, "percentage", False)
        if self.value is None and self.remainder_wording is None:
            object.__setattr__(self, "remainder_wording", "remaining")

    def scale(self, factor: Union[int, float, Fraction]) -> "Proportion":
        return self  # Nothing to rescale


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

    def scale(self, factor: Union[int, float, Fraction]) -> "RecipeTreeNode":
        raise NotImplementedError()


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

    def scale(self, factor: Union[int, float, Fraction]) -> "Ingredient":
        return replace(
            self,
            description=self.description.scale(factor),
            quantity=(
                self.quantity.scale(factor) if self.quantity is not None else None
            ),
        )


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
                self,
                inputs=tuple(node.substitute(old, new) for node in self.inputs),
            )

    def scale(self, factor: Union[int, float, Fraction]) -> "Step":
        return replace(
            self,
            description=self.description.scale(factor),
            inputs=tuple(input.scale(factor) for input in self.inputs),
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

    def substitute(self, old: RecipeTreeNode, new: RecipeTreeNode) -> RecipeTreeNode:
        if self == old:
            return new
        else:
            return replace(
                self,
                sub_recipe=cast(Reference, self.sub_recipe.substitute(old, new)),
            )

    def scale(self, factor: Union[int, float, Fraction]) -> "Reference":
        return replace(
            self,
            sub_recipe=self.sub_recipe.scale(factor),
            amount=self.amount.scale(factor),
        )


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
    just be a distraction and so this setting should be False.
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
            return replace(
                self,
                sub_tree=self.sub_tree.substitute(old, new),
            )

    def scale(self, factor: Union[int, float, Fraction]) -> "SubRecipe":
        return replace(
            self,
            sub_tree=self.sub_tree.scale(factor),
            output_names=tuple(
                output_name.scale(factor) for output_name in self.output_names
            ),
        )


@dataclass(frozen=True)
class Recipe:
    """
    A recipe, defined in terms of a series of recipe trees. Later trees may
    reference the outputs of earlier trees resulting in a Directed Acyclic
    Graph (DAG) structure describing a recipe.
    """

    recipe_trees: Tuple[RecipeTreeNode, ...]
    """
    The recipe tree roots for this :py:class:`Recipe`.
    """

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

    def scale(self, factor: Union[int, float, Fraction]) -> "Recipe":
        """
        Return a copy of this recipe with all scalable values and quantities
        scaled by the given factor.
        """
        return replace(
            self,
            recipe_trees=tuple(
                recipe_tree.scale(factor) for recipe_tree in self.recipe_trees
            ),
            follows=(self.follows.scale(factor) if self.follows is not None else None),
        )
