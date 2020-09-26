"""
A directory structure containing recipe grid markdown recipes.
"""

from typing import Mapping, Optional, Tuple

from pathlib import Path

from html import unescape

import re

import marko  # type: ignore

from peggie import ParseError

from recipe_grid.compiler import RecipeCompileError
from recipe_grid.markdown import compile_markdown, MarkdownRecipe


class RecipeDirectoryError(Exception):
    """Base class for exceptions thrown when a recipe directory is malformed."""


class NotADirectoryError(RecipeDirectoryError):
    """Thrown when a path given is not a directory."""


class MultipleIndexError(RecipeDirectoryError):
    """Thrown when a recipe directory contains multiple index.md or readme.md files."""


class RecipeInDirectoryCompileError(RecipeDirectoryError):
    """Thrown when a recipe found in a directory fails to compile."""


class IndexMissingTitleError(RecipeDirectoryError):
    """Thrown when an index.md file is missing a <h1> level title."""


class IndexMalformedTitleError(RecipeDirectoryError):
    """Thrown when an index.md file's <h1> title contains anything but simple text."""


class RecipeMissingTitleError(RecipeDirectoryError):
    """Thrown when an recipe does not have a title."""


class RecipeMissingServingsError(RecipeDirectoryError):
    """Thrown when an recipe does not have a serving count."""


def filename_to_title(filename: str) -> str:
    """
    Given a filename in snake case, camel case or containing Real Spaces(TM),
    returns a normalised rendering. For example "myDirName" and "MY_DIR_NAME"
    would become "My dir name".
    """
    # Surround numbers in whitespace
    filename = re.sub(r"[0-9]+", lambda match: f" {match.group(0)} ", filename,)

    # Convert camel-case word boundaries into spaces
    filename = re.sub(
        r"([^A-Z])([A-Z])",
        lambda match: " ".join(g for g in match.groups() if g is not None),
        filename,
    )

    # Normalise punctuation/spaces into single spaces
    filename = re.sub(r"[^a-zA-Z0-9]+", " ", filename).strip()

    # Normalise case
    return " ".join(
        word.title() if i == 0 else word.lower()
        for i, word in enumerate(filename.split())
    )


def compile_readme_markdown(path: Path) -> Tuple[str, str]:
    """
    Read and compile a markdown 'index' document, stripping the <h1> heading
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
        raise IndexMissingTitleError(f"{path} must start with a h1-level title.")

    title = first_line[len("<h1>") : -len("</h1>")]
    if "<" in title:
        raise IndexMalformedTitleError(
            f"{path} must have only simple text in its  h1 title"
        )

    title = unescape(title)
    description = "".join(lines[1:])

    return title, description


class RecipeDirectory:
    directory: Path
    """The file system directory this refers to."""

    title: str
    """The title which describes this directory."""

    description: str
    """HTML describing the contents of this directory."""

    subdirectories: Mapping[Path, "RecipeDirectory"]

    recipes: Mapping[Path, MarkdownRecipe]

    def __init__(self, directory: Path) -> None:
        if not directory.is_dir():
            raise NotADirectoryError(f"{directory} is not a directory")
        self.directory = directory

        readme_path: Optional[Path] = None
        self.subdirectories = {}
        self.recipes = {}

        for path in directory.iterdir():
            if path.is_dir():
                subdir = RecipeDirectory(path)
                if subdir:  # Don't include non-recipe containing directories
                    self.subdirectories[path] = subdir
            elif path.name.lower() in ("index.md", "readme.md"):
                if readme_path is None:
                    readme_path = path
                else:
                    raise MultipleIndexError(
                        f"{path} contains multiple index files: "
                        f"{readme_path.name} and {path.name}."
                    )
            elif path.suffix.lower() == ".md":
                with path.open() as f:
                    try:
                        recipe = self.recipes[path] = compile_markdown(f.read())
                    except (RecipeCompileError, ParseError) as e:
                        raise RecipeInDirectoryCompileError(
                            f"Error while compiling {path}: {e}"
                        )

                    if recipe.title is None:
                        raise RecipeMissingTitleError(
                            f"Recipe {path} is missing a title"
                        )
                    if recipe.servings is None:
                        raise RecipeMissingServingsError(
                            f"Recipe {path} is missing a number of "
                            f"servings (e.g. '... for 3' in the title)"
                        )

        if readme_path is None:
            self.title = filename_to_title(directory.resolve().name)
            self.description = ""
        else:
            self.title, self.description = compile_readme_markdown(path)

    def __bool__(self) -> bool:
        """True if this directory contains at least one recipe."""
        return bool(self.recipes) or any(d for d in self.subdirectories)
