# Configuration file for the Sphinx documentation builder.
#
# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys

sys.path.insert(0, os.path.abspath("../../recipe_grid"))


# -- Project information -----------------------------------------------------

project = "Recipe Grid"
copyright = "2020, Jonathan Heathcote"
author = "Jonathan Heathcote"

# The full version, including alpha/beta/rc tags
from recipe_grid import __version__

release = __version__


# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.graphviz",
    "numpydoc",
    "recipe_grid.sphinx_ext",
]

templates_path = []

exclude_patterns = []

# Fixes numpydoc autosummary errors
numpydoc_show_class_members = False

# Order members in source order, not alphabetically
autodoc_member_order = "bysource"

# Pull in references to other Python code's docs
intersphinx_mapping = {
    "python": ("http://docs.python.org/3", None),
    "peggie": ("https://peggie.readthedocs.io/en/latest/", None),
    "marko": ("https://marko-py.readthedocs.io/en/latest/", None),
}

# -- Options for HTML output -------------------------------------------------

html_theme = "nature"

html_static_path = ["_static"]
