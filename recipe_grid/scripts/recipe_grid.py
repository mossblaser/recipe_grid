"""
The ``recipe-grid`` command for compiling a single recipe into a stand-alone
HTML page.
"""

import sys

from argparse import ArgumentParser

from pathlib import Path

from recipe_grid.number_parser import number

from recipe_grid.static_site.exceptions import StaticSiteError

from recipe_grid.static_site.standalone_page import generate_standalone_page


def main() -> None:
    parser = ArgumentParser(
        description="""
            Compile a recipe grid markdown file into a standalone HTML page.
        """,
    )

    parser.add_argument(
        "recipe",
        type=Path,
        help="""
            The filename of the recipe grid markdown file to compile.
        """,
    )
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=None,
        help="""
            The output filename for the generated HTML file. Defaults to the
            input filename with the extension replaced with .html if no name is
            given.
        """,
    )

    scaling_group = parser.add_mutually_exclusive_group()

    scaling_group.add_argument(
        "--servings",
        "-s",
        type=int,
        metavar="SERVINGS",
        default=None,
        help="""
            Rescale the recipe to serve the specified number of servings. This
            option requires that the recipe declares the number of servings it
            makes in its title (e.g. the title should end with 'for <N>').
        """,
    )

    scaling_group.add_argument(
        "--scale",
        "-S",
        type=number,
        metavar="MULTIPLIER",
        default=None,
        help="""
            Multiplier to scale the recipe by. May be a decimal (e.g. '3' or
            '3.14') or a fraction (e.g. '1/2' or '9 3/4').
        """,
    )

    parser.add_argument(
        "--embed-local-links",
        "-e",
        action="store_true",
        help="""
            Replace all local link and image URLs with data: URLs embedding the
            linked resource directly into the HTML. This is the default mode.
        """,
    )
    parser.add_argument(
        "--no-embed-local-links",
        "-E",
        action="store_false",
        dest="embed_local_links",
        help="""
            Leave local link and image URLs as they are.
        """,
    )

    args = parser.parse_args()

    try:
        html = generate_standalone_page(
            args.recipe,
            servings=args.servings,
            scale=args.scale,
            embed_local_links=args.embed_local_links,
        )
    except StaticSiteError as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)

    output = args.output
    if output is None:
        output = args.recipe.with_suffix(".html")

    with output.open("w") as f:
        f.write(html)


if __name__ == "__main__":
    main()
