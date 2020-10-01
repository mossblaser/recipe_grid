"""
The ``recipe-grid-site`` command for compiling a directory hierarchy of recipes
into a (static) recipe website.
"""

import sys

from argparse import ArgumentParser

from pathlib import Path

from recipe_grid.static_site.exceptions import StaticSiteError

from recipe_grid.static_site.website import generate_static_site


def main() -> None:
    parser = ArgumentParser(
        description="""
            Compile a directory hierarchy of recipe grid markdown files into a
            static recipe website.
        """,
    )

    parser.add_argument(
        "recipes",
        type=Path,
        help="""
            The directory containing the recipes.
        """,
    )
    parser.add_argument(
        "output",
        type=Path,
        help="""
            The directory to write the generated website to. Will be created if
            it does not exist. Should be empty. Files already in this directory
            may be overwritten silently.
        """,
    )

    parser.add_argument(
        "--max-servings",
        "-s",
        type=int,
        default=10,
        help="""
            The maximum number of servings to scale each recipe to. Must be at
            least as many servings as the largest number of servings originally
            used by any recipe. Default: %(default)s.
        """,
    )

    args = parser.parse_args()

    try:
        generate_static_site(
            args.recipes, args.output, max_servings=args.max_servings,
        )
    except StaticSiteError as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
