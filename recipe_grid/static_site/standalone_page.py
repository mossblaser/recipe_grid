"""
Generates a stand alone HTML page for a single recipe.
"""

from typing import Union, Optional

from fractions import Fraction

from functools import partial

from pathlib import Path

# NB: Used in favour of recipe_grid.markdown.compile_markdown due to unified
# exceptions.
from recipe_grid.static_site.recipe_directory import compile_recipe_markdown

from recipe_grid.static_site.templates import standalone_recipe_template

from recipe_grid.static_site.html_postprocessing import (
    postprocess_html,
    embed_local_links_as_data_urls,
)


def generate_standalone_page(
    input_file: Path,
    scale: Optional[Union[int, float, Fraction]] = None,
    servings: Optional[int] = None,
    embed_local_links: bool = True,
) -> str:
    """
    Generate a standalone page with a rendered markdown recipe.

    Parameters
    ==========
    input_file : Path
        The file containing the recipe grid markdown file to compile.
    scale : number or None
        If given, scales the recipe by the provided factor (e.g. scale=2 will
        double all quantities). Must not be given if 'servings' is used.
    servings : int or None
        If given, scales the recipe to the specified number of servings. Will
        fail if the recipe does not specify the number of servings it makes in
        its title. Must not be given if 'scale' is used.
    embed_local_links : bool
        If True, links to local files will be replaced by ``data:`` URLs with
        the referenced file contents embedded.
    """
    recipe = compile_recipe_markdown(
        input_file,
        require_title=False,
        require_servings=servings is not None,
    )

    if scale is not None:
        assert servings is None
    elif servings is not None:
        scale = Fraction(servings, recipe.servings)
    else:
        scale = 1

    recipe_html = recipe.render(scale)

    if embed_local_links:
        recipe_html = postprocess_html(
            recipe_html,
            complete_document=True,
            stages=[
                partial(
                    embed_local_links_as_data_urls,
                    source=input_file,
                    root=input_file.parent,
                ),
            ],
        )

    return standalone_recipe_template.render(
        title=recipe.title if recipe.title is not None else "Recipe",
        body=recipe_html,
    )
