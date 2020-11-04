"""
The ``recipe-grid-site`` command generates recipe book style websites from a
directory of Markdown recipe sources.

Given a directory containing a collection of recipes (as detailed below) the
static site generator is used like so::

    $ recipe-grid-site INPUT_DIR OUTPUT_DIR

Generated websites are entirely static and may be browsed locally or hosted
using any static web hosting service.

Input directory structure
=========================

Each recipe should be placed in its own Markdown file, using a ``.md``
extension. These may be placed in a single directory or organised into a
hierarchy of subdirectories. When subdirectories are used, the generated
website will allow visitors to browse the recipes according to this structure.

An example hierarchy is illustrated below::

    +- my_recipe_website/
    |  +- pasta/
    |  |  +- spag_bol.md
    |  |  +- lasagne.md
    |  |  ...
    |  +- indian/
    |  |  +- mains/
    |  |  |  +- channa_masala.md
    |  |  |  +- tikka_masala.md
    |  |  +- sides/
    |  |  |  +- saag_aloo.md
    |  |  |  +- roti.md
    |  |  ...
    |  ...

Recipe Markdown files must start with a H1-level title giving the name of the
recipe. If this title indicates the number of servings (e.g. 'Tiffin for 2'),
the website will include scaled versions of this recipe to serve between 1 and
10 people (by default). If the number of servings is not indicated, the recipe
will not be scaled and will appear with quantities left as-is.

.. note::

    The maximum serving count shown on the website may be changed from the
    default of 10 using the ``--max-servings`` or ``-s`` argument. The value
    chosen must be at least as large as the largest number of servings any
    recipe is given for.

By default, the recipe website's name and category names are inferred from the
directory names. In the example above, for instance, the website would be named
"My recipe website" and the categories "Pasta", "Indian" and so on. Directory
name are automatically prettified and may be named using ``snake_case``,
``CammelCase`` or ``contain real spaces``.


Readme files
============

You can optionally add a readme files (named ``README.md`` or ``index.md``) to
your directory hierarchy in order customise the website and category names and
to add introductory text.

.. note::

    It doesn't matter if you use ``index.md`` or ``README.md``: both work,
    choose whatever brings you the most fulfilment in life.

The contents of the readme file in the top directory, if provided, will be
shown on the homepage while readme files in subdirectories will be shown on
their respective category browsing pages.

Readme files must start with a H1-level title giving the name for the website
(in the case of the top-level readme) or the name of the category (for other
readme files). These titles override the titles automatically inferred from the
directory names.

These Markdown files are processed as vanilla `CommonMark Markdown
<https://commonmark.org/>`_ and cannot contain recipes themselves.


Links and images
================

All local files and images linked to or used in recipe and readme Markdown
files will be copied into the generated static website.

Links to a recipe markdown file within the site will be rewritten as links to
the compiled recipe page on the website.

Links to subdirectories or readme Markdown files will be rewritten to point to
the corresponding category browsing page.

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
            args.recipes,
            args.output,
            max_servings=args.max_servings,
        )
    except StaticSiteError as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
