"""
A Sphinx extension for embedding compiled recipes in HTML outputs.

This extension is enabled by adding ``"recipe_grid.sphinx_ext"`` to your
Sphinx extensions list.

.. highlight:: rst

This extension adds a ``recipe`` directive which may be used to insert recipe
grid tables into (HTML-only) sphinx documentation. For example::

    .. recipe::
        1 can of spam, sliced
        1 egg, boiled

        fried spam and eggs = fry(spam, egg)

Produces the following output:

.. recipe::
    1 can of spam, sliced
    1 egg, boiled

    fried spam and eggs = fry(spam, egg)

Referencing earlier recipes
===========================

Recipes may be defined across several blocks with later blocks referencing
outputs from earlier blocks. For example::

    .. recipe::
        serve(
            fried spam and eggs,
            more spam,
        )

.. recipe::
    serve(
        fried spam and eggs,
        more spam,
    )

Starting a new recipe
=====================

A new, independent recipe may be started by adding the ``:start-new-recipe:``
option enabling ingredient/output names to be reused without referring to
earlier recipes. For example::

    .. recipe::
        :start-new-recipe:

        1 egg, scrambled

.. recipe::
    :start-new-recipe:

    1 egg, scrambled

Scaling
=======

Recipes can be scaled using the ``:scale:`` option::

    .. recipe::
        :scale: 3/2

        1 packet of cupcake batter
        bake(
            pre-heat oven,
            put into {4} cupcake cases(cupcake batter)
        )

.. recipe::
    :scale: 3/2

    1 packet of cupcake batter
    bake(
        pre-heat oven,
        put into {4} cupcake cases(cupcake batter)
    )


.. warning::
    The ``:scale:`` option only scales the recipe shown for the given
    ``recipe`` directive. Where a recipe is given in several blocks, the
    ``:scale:`` option must be repeated otherwise the displayed values will be
    inconsistent.


Showing sources
===============

To facilitate writing of documentation examples for the recipe grid syntax, the
``:show-source:`` option may be used which will cause the rendered recipe grid
table to be shown adjacent to the recipe grid source which defines it. For
example::

    .. recipe::
        :show-source:

        1 oven pizza
        slice(
            bake(
                pre-heat oven,
                oven pizza,
            )
        )

Will be rendered as:

.. recipe::
    :show-source:

    1 oven pizza
    slice(
        bake(
            pre-heat oven,
            oven pizza,
        )
    )

Internals
=========

This Sphinx extension runs as follows:

1. The ``builder-inited`` Sphinx event is used to add the recipe grid CSS to the
   site.
2. For each page in the documentation, recipes are compiled as follows:
    a. ``recipe`` directives turn into ``pending_recipe_node`` nodes and
       capture the recipe grid source in ``env.recipe_sources`` (see
       :py:meth:`RecipeDirective.run`).
    b. In the ``doctree-read`` Sphinx event (called after each page has been
       read and the directives expanded) compiles the recipes into recipe
       grid abstract recipe descriptions (see :py:mod`recipe_grid.recipe`) and
       stores these in the ``pending_recipe_node`` objects.
3. During HTML rendering, ``pending_recipe_node`` nodes are replaced with
   rendered recipe tables.

"""

from typing import Union, List, Mapping, Any

import os

from collections import defaultdict

from fractions import Fraction

from docutils import nodes
from docutils.parsers.rst.directives import flag

from sphinx.application import Sphinx
from sphinx.errors import SphinxError
from sphinx.util.docutils import SphinxDirective
from sphinx.writers.html import HTMLTranslator

from peggie import ParseError

from recipe_grid import __version__
from recipe_grid.compiler import compile, RecipeCompileError
from recipe_grid.recipe import Recipe
from recipe_grid.renderer.html import t, render_recipe_tree
from recipe_grid.static_site.templates import tables_only_css_template
from recipe_grid.number_parser import number


class SphinxRecipeCompileError(SphinxError):
    """Thrown when a recipe fails to compile."""


class RecipeDirective(SphinxDirective):

    has_content = True

    option_spec = {
        "scale": number,
        "show-source": flag,
        "start-new-recipe": flag,
    }

    def run(self) -> List[nodes.Node]:
        # The recipes in a doctree are accumulated in env.recipe_sources in the
        # form:
        #
        #    {docname: [[(source, node), ...], ...], ...}
        #
        # Where the inner most lists contain a complete recipe's complete set
        # of source blocks along with the associated pending_recipe_node
        # placeholder object. The 'source' strings will be padded with leading
        # newlines so that line numbers match their positions in the RST
        # document.
        if not hasattr(self.env, "recipe_sources"):
            self.env.recipe_sources = defaultdict(list)  # type: ignore

        page_recipes = self.env.recipe_sources[self.env.docname]  # type: ignore

        if len(page_recipes) == 0 or "start-new-recipe" in self.options:
            page_recipes.append([])

        # Extract the recipe and replace with a pending_recipe_node
        page_recipe_blocks = page_recipes[-1]
        source = "\n".join(self.content)
        padded_source = "\n" * self.content_offset + source
        node = pending_recipe_node()
        node.scale = self.options.get("scale", 1)
        page_recipe_blocks.append((padded_source, node))

        if "show-source" in self.options:
            return [
                nodes.literal_block(text=source, language="text"),
                node,
            ]
        else:
            return [node]


def compile_recipes(app: Sphinx, doctree: nodes.Node) -> None:
    """Parse and compile the recipes appearing on a page."""
    env = app.env

    # Skip if no recipe sources found anywhere
    if not hasattr(env, "recipe_sources"):
        return

    docname = env.docname

    page_recipes = env.recipe_sources[docname]  # type: ignore

    for i, page_recipe_blocks in enumerate(page_recipes):
        sources = [source for source, _node in page_recipe_blocks]
        try:
            recipes = compile(sources)
        except (ParseError, RecipeCompileError) as e:
            filename = env.doc2path(docname)
            raise SphinxRecipeCompileError(f"Recipe compile error in {filename}: {e}")

        for (_source, node), recipe in zip(page_recipe_blocks, recipes):
            node.id_prefix = f"sub-recipe-{i}-"
            node.recipe = recipe


class pending_recipe_node(nodes.Element):  # type: ignore
    # Set when the node is created by RecipeDirective.run
    scale: Union[int, float, Fraction]

    # The following fields are assigned by compile_recipes
    id_prefix: str
    recipe: Recipe


def visit_pending_recipe_node(self: HTMLTranslator, node: nodes.Node) -> None:
    self.body.append(
        t(
            "div",
            "\n".join(
                render_recipe_tree(recipe_tree, node.id_prefix)
                for recipe_tree in node.recipe.scale(node.scale).recipe_trees
            ),
            class_="rg-recipe-block",
        )
    )


def depart_pending_recipe_node(self: HTMLTranslator, node: nodes.Node) -> None:
    pass


def copy_stylesheet(app: Sphinx) -> None:
    if app.builder.format == "html":
        static_dir = os.path.join(app.builder.outdir, "_static")
        os.makedirs(static_dir, exist_ok=True)
        filename = "recipe_grid_tables.css"
        with open(os.path.join(static_dir, filename), "w") as f:
            f.write(tables_only_css_template.render())
        app.add_css_file(filename)


def setup(app: Sphinx) -> Mapping[str, Any]:
    app.connect("builder-inited", copy_stylesheet)

    app.add_directive("recipe", RecipeDirective)

    app.connect("doctree-read", compile_recipes)

    app.add_node(
        pending_recipe_node,
        html=(visit_pending_recipe_node, depart_pending_recipe_node),
    )

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
