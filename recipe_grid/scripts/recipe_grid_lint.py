"""
The ``recipe-grid-lint`` command for linting recipes for possible mistakes.
"""

import sys

from argparse import ArgumentParser

from pathlib import Path

from peggie import ParseError
from recipe_grid.compiler import RecipeCompileError

from recipe_grid.markdown import compile_markdown

from recipe_grid.lint import check, LintKind


def main() -> None:
    parser = ArgumentParser(
        description="""
            Check a recipe grid markdown file for possible mistakes.
        """,
    )

    parser.add_argument(
        "recipe",
        type=Path,
        nargs="*",
        help="""
            The filename of the recipe grid markdown file to compile. Pass
            multiple filenames to check multiple files.
        """,
    )

    parser.add_argument(
        "--ignore",
        "-i",
        action="extend",
        default=[],
        nargs="+",
        choices=[k.name for k in LintKind],
        help="""
            Ignore warnings of a certain types.
        """,
    )

    args = parser.parse_args()

    failed = False
    for page in args.recipe:
        try:
            markdown_recipe = compile_markdown(page.open().read())
            for recipe in markdown_recipe.recipes:
                for lint in check(recipe):
                    if lint.kind.name not in args.ignore:
                        failed = True
                        print(f"{page}: Warning: {lint.description} [{lint.kind.name}]")
        except (ParseError, RecipeCompileError) as e:
            failed = True
            print(f"{page}: Error: {e}")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
