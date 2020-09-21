"""
Routines for extracting the recipe grid sources from a Markdown file.
"""

from typing import List, cast

from marko import Markdown  # type: ignore

from recipe_grid.markdown.common import (
    RecipeSourceBlock,
    RecipeGridBaseRendererMixin,
    Document,
    CodeBlock,
    FencedCode,
)


class RecipeGridSourceExtractorRendererMixin(RecipeGridBaseRendererMixin):
    def render_recipe_source_block(self, element: RecipeSourceBlock) -> str:
        return str(element.pos)

    def render_document(self, element: Document) -> List[List[str]]:  # type: ignore
        print(super().render_document(element))
        return [
            [
                recipe_source_block.get_line_number_corrected_source(
                    self.markdown_source
                )
                for recipe_source_block in recipe_source_blocks.values()
            ]
            for recipe_source_blocks in self.independent_recipe_source_blocks
        ]


class RecipeGridExtractor:
    elements = [Document, CodeBlock, FencedCode]
    renderer_mixins = [RecipeGridSourceExtractorRendererMixin]


def extract_recipe_sources_from_markdown(markdown_source: str) -> List[List[str]]:
    """
    Extract the recipe sources contained in a markdown document.

    Returns
    =======
    [[recipe_source_block, ...], ...]
        The extracted source code within the recipe code blocks of the supplied
        document.

        Sources are provided in document order, grouped into independent
        recipes as delineated by the use of ``new-recipe`` blocks.

        Each source string has newlines prepended such that line numbers in the
        strings correspond with line numbers in the markdown source
        facilitating better error messages.
    """
    return cast(
        List[List[str]], Markdown(extensions=[RecipeGridExtractor])(markdown_source)
    )
