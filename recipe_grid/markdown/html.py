"""
A :py:mod:`marko` extension for compiling markdown with recipe grid code blocks
into HTML.
"""

from typing import cast

import random

import string

from marko import Markdown  # type: ignore

from recipe_grid.compiler import compile
from recipe_grid.renderer.recipe_to_table import recipe_tree_to_table
from recipe_grid.renderer.html import render_table, t

from recipe_grid.markdown.common import (
    RecipeSourceBlock,
    RecipeGridBaseRendererMixin,
    Document,
    CodeBlock,
    FencedCode,
)


def generate_random_string(num_random_chars: int = 32) -> str:
    """
    Generate a long random ASCII string for use as a unique replacement string
    to temporarily insert into markdown HTML output and later substitute for a
    compiled recipe table.
    """
    slug = "".join(
        random.choice(string.ascii_uppercase) for _ in range(num_random_chars)
    )
    return f"%{slug}%"


class RecipeGridHTMLRendererMixin(RecipeGridBaseRendererMixin):
    def render_recipe_source_block(self, _element: RecipeSourceBlock) -> str:
        return generate_random_string()

    def render_document(self, element: Document) -> str:
        final_output = super().render_document(element)

        for recipe_source_blocks in self.independent_recipe_source_blocks:
            replacement_strings = list(recipe_source_blocks.keys())
            sources = [
                recipe_source_block.get_line_number_corrected_source(
                    self.markdown_source
                )
                for recipe_source_block in recipe_source_blocks.values()
            ]
            recipes = compile(sources)
            tables = [
                t(
                    "div",
                    "\n".join(
                        render_table(recipe_tree_to_table(recipe_tree))
                        for recipe_tree in recipe.recipe_trees
                    ),
                    class_="rg-recipe",
                )
                for recipe in recipes
            ]

            for replacement_string, table in zip(replacement_strings, tables):
                final_output = final_output.replace(replacement_string, table)

        return final_output


class RecipeGrid:
    """
    A :py:mod:`marko` extension which compiles recipes within the markdown
    source into HTML tables.
    """

    elements = [Document, CodeBlock, FencedCode]
    renderer_mixins = [RecipeGridHTMLRendererMixin]


def render_markdown(markdown_source: str) -> str:
    """
    Render a markdown document, along with all embedded recipe descriptions,
    into HTML.

    Internally calls :py:func:`recipe_grid.compiler.compile` and so may throw
    the same kinds of exceptions when syntax errors in the recipe sources are
    encountered.
    """
    return cast(str, Markdown(extensions=[RecipeGrid])(markdown_source))
