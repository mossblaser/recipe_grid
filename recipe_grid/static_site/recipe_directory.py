"""
Utilities for enumerating categorised recipes within a directory hierarchy.

Recipes may be arranged in a hierarchy of directories (for example) according
to categories and subcategories. All files with a ``.md`` extension are assumed
to be a recipe grid markdown file describing a single recipe.

Directories may optionally contain an ``index.md`` or ``README.md`` file which
better describes the directory contents. This markdown document must contain a
H1 title at the start which will be used as the user-facing category name. When
no such file is present, the category name will be a prettified version of the
directory name (see :py:func:`dirname_to_title`).
"""

from typing import Tuple, NamedTuple, Optional, List

from pathlib import Path

from functools import lru_cache

import re

import marko  # type: ignore

from html import unescape

from peggie import ParseError
from recipe_grid.compiler import RecipeCompileError

from recipe_grid.markdown import compile_markdown, MarkdownRecipe

from recipe_grid.static_site.exceptions import (
    ReadmeMissingTitleError,
    ReadmeMalformedTitleError,
    RecipeInDirectoryCompileError,
    RecipeMissingTitleError,
    RecipeMissingServingsError,
    MultipleReadmeError,
)


def dirname_to_title(filename: str) -> str:
    """
    Given a filename in snake case, camel case or containing Real Spaces(TM),
    returns a normalised rendering. For example "myDirName", "MY_DIR_NAME" and
    "My dir name" would all become "My dir name".
    """
    # Surround numbers in whitespace
    filename = re.sub(
        r"[0-9]+",
        lambda match: f" {match.group(0)} ",
        filename,
    )

    # Add spaces at camel-case word boundaries
    filename = re.sub(
        r"([^A-Z])([A-Z])",
        lambda match: " ".join(g for g in match.groups() if g is not None),
        filename,
    )

    # Replace all runs of punctuation/spaces into single spaces
    filename = re.sub(r"[^a-zA-Z0-9]+", " ", filename)

    # Strip leading/trailing spaces
    filename = filename.strip()

    # Normalise case
    return " ".join(
        word.title() if i == 0 else word.lower()
        for i, word in enumerate(filename.split())
    )


def compile_readme_markdown(path: Path) -> Tuple[str, str]:
    """
    Read and compile a markdown 'README' document, stripping the <h1> heading
    and returning the title and remainder of the document separately.

    Returns
    =======
    title: str
        The title (free from HTML escape sequences)
    description: str
        The remainder of the compiled markdown HTML source.
    """

    with path.open() as f:
        html = marko.Markdown()(f.read())

    lines = html.splitlines(keepends=True)

    first_line = (lines[0] if lines else "").strip()
    if not (first_line.startswith("<h1>") and first_line.endswith("</h1>")):
        raise ReadmeMissingTitleError(f"{path} must start with a h1-level title.")

    title = first_line[len("<h1>") : -len("</h1>")]
    if "<" in title:
        raise ReadmeMalformedTitleError(
            f"{path} must have only simple text in its  h1 title"
        )

    title = unescape(title)
    description = "".join(lines[1:])

    return title, description


_cached_compile_markdown = lru_cache(compile_markdown)
"""Used in :py:func:`compile_recipe`."""


def compile_recipe_markdown(
    recipe_source: Path, require_title: bool = True, require_servings: bool = True
) -> MarkdownRecipe:
    """
    Compile a recipe from source, converting compilation errors into
    :py:exc:`~RecipeInDirectoryCompileError` and optionally throwing
    :py:exc:`~RecipeMissingTitleError` and
    :py:exc:`~RecipeMissingServingsError` if the title or serving count are not
    given for the recipe.
    """
    with recipe_source.open() as f:
        try:
            # NB: Because we cache based on the markdown contents we will never
            # produce a stale result.
            recipe = _cached_compile_markdown(f.read())
        except (RecipeCompileError, ParseError) as e:
            raise RecipeInDirectoryCompileError(
                f"Error while compiling {recipe_source}: {e}"
            )
    if require_title and recipe.title is None:
        raise RecipeMissingTitleError(f"Recipe {recipe_source} is missing a title")
    if require_servings and recipe.servings is None:
        raise RecipeMissingServingsError(
            f"Recipe {recipe_source} is missing a number of "
            f"servings (e.g. '... for 3' in the title)"
        )

    return recipe


class RecipeDirectoryListing(NamedTuple):
    title: str
    """
    The user-facing title for this directory. Taken from the README if present,
    otherwise generated from the directory name.
    """

    description_html: Optional[str]
    """
    If a README is present, the rendered markdown content, excluding the <h1>
    block.
    """

    description_source: Optional[Path]
    """If a README is present, its filename."""

    subdirectories: List[Path]
    """The subdirectories in this listing, in no particular order."""

    recipes: List[Path]
    """The recipes in this directory in no particular order."""


def enumerate_recipe_directory(directory: Path) -> RecipeDirectoryListing:
    """
    Enumerate the contents of a recipe website directory.
    """
    if not directory.is_dir():
        raise NotADirectoryError(f"{directory} is not a directory")

    description_source: Optional[Path] = None
    subdirectories: List[Path] = []
    recipes: List[Path] = []

    for path in directory.iterdir():
        if path.is_dir():
            subdirectories.append(path)
        elif path.name.lower() in ("readme.md", "index.md"):
            if description_source is None:
                description_source = path
            else:
                raise MultipleReadmeError(
                    f"{directory} contains multiple readme files: "
                    f"{description_source.name} and {path.name}."
                )
        elif path.suffix.lower() == ".md":
            recipes.append(path)

    title: str
    description_html: Optional[str]
    if description_source is None:
        title = dirname_to_title(directory.resolve().name)
        description_html = None
    else:
        title, description_html = compile_readme_markdown(description_source)

    return RecipeDirectoryListing(
        title=title,
        description_html=description_html,
        description_source=description_source,
        subdirectories=subdirectories,
        recipes=recipes,
    )
