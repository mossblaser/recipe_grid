"""
The recipe description language is compiled into the recipe Grid data model
(see :py:mod:`recipe_grid.recipe`) by the following function:

.. autofunction:: recipe_grid.compiler.compile

During compilation the following exception types may be thrown. In all cases,
when cast to :py:class:`str`, the string representation takes the form similar
to:

.. code:: text

    At line 19 column 2:
        ))
         ^
    Expected ','

With a line number, code snippet and error explanation provided.

.. exception:: peggie.ParseError
    :noindex:

    Thrown if parsing fails due to a syntactic error (see
    :py:exc:`peggie.ParseError` in the :py:mod:`peggie` documentation for
    details).

.. autoexception:: RecipeCompileError

.. autoexception:: NameRedefinedError

.. autoexception:: ProportionGivenForIngredientError
"""

from typing import cast, List, MutableMapping, Optional, Union, Tuple

from peggie.error_message_generation import (
    offset_to_line_and_column,
    extract_line,
    format_error_message,
)

from dataclasses import dataclass, field

from collections import OrderedDict

from recipe_grid.scaled_value_string import ScaledValueString

from recipe_grid.parser import parse, ast

from recipe_grid.recipe import (
    Recipe,
    RecipeTreeNode,
    SubRecipe,
    Reference,
    Ingredient,
    Step,
    Quantity,
    Proportion,
)


@dataclass
class RecipeCompileError(ValueError):
    """Base type for compilation errors."""

    line: int
    column: int
    snippet: str
    """The source code location and snippet of the cause of the problem."""

    @property
    def explanation(self) -> str:
        raise NotImplementedError()

    def __str__(self) -> str:
        return format_error_message(
            self.line, self.column, self.snippet, self.explanation
        )


@dataclass
class NameRedefinedError(RecipeCompileError):
    """Thrown when an output name is redefined."""

    second_output_name_definition: ast.String
    """
    The AST node where the second name was redefined.
    """

    @property
    def explanation(self) -> str:
        name = compile_string(self.second_output_name_definition)
        return f"The name {name} has already been defined as a sub recipe."

    @classmethod
    def from_output_name(
        cls, source: str, output_name: ast.String
    ) -> "NameRedefinedError":
        line, column = offset_to_line_and_column(source, output_name.offset)
        snippet = extract_line(source, line)
        return cls(line, column, snippet, output_name)


@dataclass
class ProportionGivenForIngredientError(RecipeCompileError):
    """
    Thrown when an ingredient is prefixed with a proportion rather than a
    quantity. This probably implies that this was intended to be a reference to
    some earlier output and the user misspelt the name.
    """

    ast_reference: ast.Reference
    """
    The AST node where the proportion was used for an ingredient
    """

    @property
    def explanation(self) -> str:
        name = compile_string(self.ast_reference.name)
        return (
            f"A proportion was given (implying a sub recipe is "
            f"being referenced) but no sub recipe named {name} exists."
        )

    @classmethod
    def from_ast_reference(
        cls, source: str, ast_reference: ast.Reference
    ) -> "ProportionGivenForIngredientError":
        line, column = offset_to_line_and_column(source, ast_reference.offset)
        snippet = extract_line(source, line)
        return cls(line, column, snippet, ast_reference)


def normalise_output_name(name: ScaledValueString) -> ScaledValueString:
    """Normalise an output name (simply ignoring case and trailing white-space)"""
    return name.strip().lower()


def infer_output_name(recipe_tree: RecipeTreeNode) -> Optional[ScaledValueString]:
    """
    Given a parsed recipe tree, if it contains a single ingredient,
    possibly processed by several steps but never combined with another
    ingredient, return that ingredient's name. Otherwise returns None.
    """
    if isinstance(recipe_tree, Ingredient):
        return recipe_tree.description
    elif isinstance(recipe_tree, Step) and len(recipe_tree.inputs) == 1:
        return infer_output_name(recipe_tree.inputs[0])
    else:
        return None


def infer_quantity(recipe_tree: RecipeTreeNode) -> Optional[Quantity]:
    """
    Given a parsed recipe tree, if it contains a single ingredient, possibly
    processed by several steps but never combined with another ingredient,
    return that ingredient's quantity. Otherwise returns None.
    """
    if isinstance(recipe_tree, Ingredient):
        return recipe_tree.quantity
    elif isinstance(recipe_tree, Step) and len(recipe_tree.inputs) == 1:
        return infer_quantity(recipe_tree.inputs[0])
    elif isinstance(recipe_tree, SubRecipe) and len(recipe_tree.output_names) == 1:
        return infer_quantity(recipe_tree.sub_tree)
    else:
        return None


def compile_string(ast_string: ast.String) -> ScaledValueString:
    return ScaledValueString(
        [
            part.string
            if isinstance(part, ast.Substring)
            else part.number
            if isinstance(part, ast.InterpolatedValue)
            else ""
            for part in ast_string.substrings
        ]
    )


@dataclass
class NamedOutput:
    name: ScaledValueString

    definition_recipe_index: int
    """
    The index of the recipe block in which this named output is defined.

    This is used to determine when a referenced sub recipe resides in a
    different block and so consequently must not be inlined.
    """

    sub_recipe: SubRecipe
    output_index: int = 0
    """The :py:class:`~SubRecipe` output."""

    references: List[Tuple[Reference, int]] = field(default_factory=list)
    """
    The set of (:py:class:`~Reference`, recipe_index) tuples referring to this
    component. (See also definition_recipe_index.)
    """

    unwrap_subrecipe_when_inlined: bool = True
    """
    True if the sub recipe should be visually identified as a SubRecipe in the
    final recipe if it is inlined.
    """

    def substitute(self, old: RecipeTreeNode, new: RecipeTreeNode) -> None:
        self.sub_recipe = cast(SubRecipe, self.sub_recipe.substitute(old, new))
        self.references = [
            (
                (
                    # NB The following cast is always safe *unless* this ref is
                    # being substituted for the subtree it points at.
                    cast(Reference, ref.substitute(old, new))
                    # In the case where it is this ref which is being inlined,
                    # keep the old Reference object, rather than letting the
                    # substitution return a SubTree and lying to the type
                    # system.  Following the inlining of a SubRecipe, the
                    # 'NamedOutput' data structure becomes essentially invalid
                    # anyway so this choice of dummy value is unimportant.
                    if old != ref
                    else ref
                ),
                ind,
            )
            for ref, ind in self.references
        ]

    @property
    def can_be_inlined(self) -> bool:
        """
        True iff this SubRecipe output can be inlined.
        """
        inferred_quantity = infer_quantity(self.sub_recipe)
        return (
            # Must have single output
            len(self.sub_recipe.output_names) == 1
            # Must be used in one place only
            and len(self.references) == 1
            # Must be defined and used in the same recipe block
            and self.references[0][1] == self.definition_recipe_index
            # The sole reference to this quantity must be for the full amount.
            and (
                (
                    isinstance(self.references[0][0].amount, Proportion)
                    and (
                        self.references[0][0].amount.value is None
                        or self.references[0][0].amount.value == 1.0
                    )
                )
                or (
                    isinstance(self.references[0][0].amount, Quantity)
                    and inferred_quantity is not None
                    and self.references[0][0].amount.has_equal_value_to(
                        inferred_quantity
                    )
                )
            )
        )


class RecipeCompiler:

    _sources: List[str]
    """
    The source code for each compiled recipe block. Used in the production of
    error messages.
    """

    _named_outputs: MutableMapping[ScaledValueString, NamedOutput]
    """
    The set of names currently defined in the recipe and the SubRecipe output
    the name refers to.
    """

    _current_recipe_index: int
    """
    The index of the recipe parse tree currently being compiled. (Set by
    :py:meth:`compile`).
    """

    def compile(self, sources: List[str]) -> List[Recipe]:
        """
        Compile a series of recipe parse trees
        (:py:class:`recipe_grid.ast.Recipe`) into a series of
        :py:class:`Recipe` structures where each structure represents a
        particular block in the input recipe specification.
        """
        self._sources = sources
        self._named_outputs = OrderedDict()

        ast_recipes = [parse(source) for source in self._sources]

        recipe_block_recipe_trees: List[List[RecipeTreeNode]] = []
        for recipe_index, ast_recipe in enumerate(ast_recipes):
            self._current_recipe_index = recipe_index
            recipe_trees: List[RecipeTreeNode] = []

            for ast_stmt in ast_recipe.stmts:
                recipe_trees.append(self._compile_stmt(ast_stmt))

            recipe_block_recipe_trees.append(recipe_trees)

        # Move SubRecipes inline where possible
        for named_output in self._named_outputs.values():
            if named_output.can_be_inlined:
                # Unwrap the to-be-inlined SubTree if needed
                tree_to_inline: RecipeTreeNode
                if named_output.unwrap_subrecipe_when_inlined:
                    tree_to_inline = named_output.sub_recipe.sub_tree
                else:
                    tree_to_inline = named_output.sub_recipe

                definition_to_remove = named_output.sub_recipe
                reference_to_replace = named_output.references[0][0]

                # Remove the original definition
                recipe_trees = recipe_block_recipe_trees[
                    named_output.definition_recipe_index
                ]
                recipe_trees.remove(definition_to_remove)

                # Apply inline-substitution
                recipe_block_recipe_trees = [
                    [
                        recipe_tree.substitute(reference_to_replace, tree_to_inline)
                        for recipe_tree in recipe_trees
                    ]
                    for recipe_trees in recipe_block_recipe_trees
                ]

                # Inline-substitution also applied to recipe trees contained in
                # NamedOutputs since otherwise when attempting to inline based
                # on these out-of-date trees would be found.
                for other_named_output in self._named_outputs.values():
                    other_named_output.substitute(reference_to_replace, tree_to_inline)

        # Create recipe objects
        previous_recipe = None
        out: List[Recipe] = []
        for recipe_trees in recipe_block_recipe_trees:
            recipe = Recipe(tuple(recipe_trees), previous_recipe)
            out.append(recipe)
            previous_recipe = recipe
        return out

    def _compile_stmt(self, ast_stmt: ast.Stmt) -> RecipeTreeNode:
        # Compile the recipe tree (the RHS of the statement)
        recipe_tree: RecipeTreeNode = self._compile_expr(ast_stmt.expr)

        # Determine the output names, if present (e.g. from the LHS of the statement)
        output_names: Tuple[ScaledValueString, ...] = ()
        output_name_inferred = False
        if ast_stmt.outputs:
            output_names = tuple(
                compile_string(output_name) for output_name in ast_stmt.outputs
            )
        else:
            inferred_output_name = infer_output_name(recipe_tree)
            if inferred_output_name is not None:
                output_name_inferred = True
                output_names = (inferred_output_name,)

        # Wrap tree in SubRecipe when named outputs have been used
        if output_names:
            recipe_tree = SubRecipe(
                sub_tree=recipe_tree,
                output_names=output_names,
                show_output_names=not output_name_inferred,
            )

            for output_index, output_name in enumerate(output_names):
                normalised_output_name = normalise_output_name(output_name)

                # Check for name conflicts
                if normalised_output_name in self._named_outputs:
                    assert ast_stmt.outputs  # For benefit of MyPy
                    raise NameRedefinedError.from_output_name(
                        self._sources[self._current_recipe_index],
                        ast_stmt.outputs[output_index],
                    )

                # Add to LUT of outputs to recipe trees
                self._named_outputs[normalised_output_name] = NamedOutput(
                    name=output_name,
                    definition_recipe_index=self._current_recipe_index,
                    sub_recipe=recipe_tree,
                    output_index=output_index,
                    unwrap_subrecipe_when_inlined=not ast_stmt.named,
                )

        return recipe_tree

    def _compile_expr(self, ast_expr: ast.Expr) -> Union[Ingredient, Step, Reference]:
        if isinstance(ast_expr, ast.Step):
            return self._compile_step(ast_expr)
        elif isinstance(ast_expr, ast.Reference):
            return self._compile_reference(ast_expr)
        else:
            raise NotImplementedError(type(ast_expr))

    def _compile_step(self, ast_step: ast.Step) -> Step:
        return Step(
            description=compile_string(ast_step.name),
            inputs=tuple(self._compile_expr(ast_expr) for ast_expr in ast_step.inputs),
        )

    def _compile_reference(
        self, ast_reference: ast.Reference
    ) -> Union[Ingredient, Reference]:
        name = compile_string(ast_reference.name)
        normalised_name = normalise_output_name(name)

        if normalised_name in self._named_outputs:
            # Name refers to a SubRecipe output, this is a Reference
            output = self._named_outputs[normalised_name]
            reference = Reference(
                sub_recipe=output.sub_recipe,
                output_index=output.output_index,
                amount=self._compile_quantity_or_proportion(
                    ast_reference.quantity_or_proportion
                ),
            )
            output.references.append((reference, self._current_recipe_index))
            return reference
        else:
            # This is an ingredient
            if isinstance(ast_reference.quantity_or_proportion, ast.Proportion):
                raise ProportionGivenForIngredientError.from_ast_reference(
                    self._sources[self._current_recipe_index],
                    ast_reference,
                )
            return Ingredient(
                description=name,
                quantity=(
                    self._compile_quantity(ast_reference.quantity_or_proportion)
                    if ast_reference.quantity_or_proportion is not None
                    else None
                ),
            )

    def _compile_quantity_or_proportion(
        self,
        ast_quantity_or_proportion: Union[ast.Quantity, ast.Proportion, None],
    ) -> Union[Quantity, Proportion]:
        if isinstance(ast_quantity_or_proportion, ast.Quantity):
            return self._compile_quantity(ast_quantity_or_proportion)
        elif isinstance(ast_quantity_or_proportion, ast.Proportion):
            return self._compile_proportion(ast_quantity_or_proportion)
        else:
            return Proportion(1.0)

    def _compile_quantity(self, ast_quantity: ast.Quantity) -> Quantity:
        unit: Optional[str] = None
        if ast_quantity.unit is not None:
            unit_string = compile_string(ast_quantity.unit)

            # The grammar disallows scaled values in unit names, this assertion
            # is just a sanity check to that effect
            assert unit_string == unit_string.scale(0)

            unit = str(unit_string)

        return Quantity(
            value=ast_quantity.value,
            unit=unit,
            value_unit_spacing=ast_quantity.value_unit_spacing,
            preposition=ast_quantity.preposition,
        )

    def _compile_proportion(self, ast_proportion: ast.Proportion) -> Proportion:
        return Proportion(
            value=ast_proportion.value,
            percentage=ast_proportion.percentage
            if ast_proportion.value is not None
            else None,
            remainder_wording=ast_proportion.remainder_wording,
            preposition=ast_proportion.preposition,
        )


def compile(sources: List[str]) -> List[Recipe]:
    """
    Compile a recipe from source into a series of
    :py:class:`recipe_grid.recipe.Recipe` data structures.

    The input recipe may be split into several blocks with later blocks
    referencing sub recipes in earlier ones. The code for each block should be
    passed separately and for each of these a separate
    :py:class:`~recipe_grid.recipe.Recipe` object will be produced.

    May throw :py:exc:`peggie.ParseError` during parsing and subclasses of
    :py:exc:`RecipeCompileError` during compilation.

    .. tip::

        It is assumed that all source blocks originate from a single file (e.g.
        from different indented blocks in a Markdown file). To make error
        messages report correct line numbers, pad the start of each source
        string with empty lines according to the position of the block in the
        original file. This will ensure that error messages give useful line
        numbers.
    """
    return RecipeCompiler().compile(sources)
