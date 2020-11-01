"""
The ``recipe-grid`` command compiles a single Markdown recipe into a
stand-alone HTML page.

.. highlight:: bash

Basic usage
===========

.. code:: text

    $ recipe-grid RECIPE_SOURCE [OUTPUT_FILENAME]

This will compile the recipe in the indicated markdown file. If no output
filename is given, the input filename with the suffix replaced with '.html' is
used.

Scaling recipes
===============

You can scale the recipe by an arbitrary factor using the ``--scale`` or ``-S``
argument. This takes integers (e.g. '2'), decimal numbers (e.g. '1.5') and
fractions (e.g. '1/2' or '1 1/3').

When the recipe begins with a H1-level title ending with a number of servings
(e.g. 'Tiffin for 2'), you can alternatively use the ``--servings`` or ``-s``
argument to scale the recipe. This argument takes a a number of servings to
scale the recipe to and computes the scaling factor for you.

Links and images
================

By default links to local files and images are embedded as ``data:`` URLs. This
means that the generated HTML page is completely standalone and does not depend
on any other files. This feature can be disabled using the
``--no-embed-local-links`` or ``-E`` flag.
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
        default=True,
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
