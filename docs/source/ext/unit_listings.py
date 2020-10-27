"""
Sphinx extension for listing units supported by :py:class:`recipe_grid.units`.

Usage::

    The following will produce a comma-separated list of all unit names and
    aliases, in alphabetical order:

    .. rgunitlist::

    The following will produce a bulleted list grouping all units by kind and
    listing aliases for each unit together:

    .. rgunitbreakdown::
"""

from typing import List, Mapping, Any

from docutils import nodes

from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective

from recipe_grid.units import UNIT_SYSTEM


class RGUnitList(SphinxDirective):
    """
    A directive which expands to a paragraph containing a comma-separated list
    of all supported unit names in alphabetical order.
    """

    def run(self) -> List[nodes.Node]:
        paragraph = nodes.paragraph(text=", ".join(sorted(UNIT_SYSTEM.iter_names())))
        return [paragraph]


class RGUnitBreakdown(SphinxDirective):
    """
    A directive which expands to a bulleted list of aliases for a particular
    unit.
    """

    def run(self) -> List[nodes.Node]:
        bullets = nodes.bullet_list()

        for unit_set_name, unit_set in UNIT_SYSTEM.unit_sets.items():
            top_item = nodes.list_item()
            bullets += top_item

            top_paragraph = nodes.paragraph(text=unit_set_name.title() + ":")
            top_item += top_paragraph

            sub_bullets = nodes.bullet_list()
            top_paragraph += sub_bullets

            for unit in unit_set.units:
                item = nodes.list_item()
                paragraph = nodes.paragraph(text=", ".join(unit.names))
                item += paragraph
                sub_bullets += item

        return [bullets]


def setup(app: Sphinx) -> Mapping[str, Any]:
    app.add_directive("rgunitlist", RGUnitList)
    app.add_directive("rgunitbreakdown", RGUnitBreakdown)

    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
