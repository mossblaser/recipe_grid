from typing import Optional, MutableMapping, List, Union, Tuple

import re

import json

import html

from textwrap import indent

from fractions import Fraction

from xml.sax.saxutils import quoteattr

from recipe_grid.scaled_value_string import ScaledValueString as SVS

from recipe_grid.renderer.table import Table, Cell, BorderType

from recipe_grid.number_formatting import format_number

from recipe_grid.units import UNIT_SYSTEM

from recipe_grid.recipe import (
    RecipeTreeNode,
    Ingredient,
    Reference,
    Step,
    SubRecipe,
    Quantity,
    Proportion,
)


def t(tag: str, body: Optional[str] = None, **attrs: str) -> str:
    """
    A simple utility function for generating HTML tags.

    Examples::

        >>> t("foo")
        '<foo />'
        >>> t("img", src="file.png")
        '<img src="file.png"/>'
        >>> t("a", "Click here", href="elsewhere.html")
        '<a href="elsewhere.html">Click here</a>'
        >>> t("span", "Hiya", class_="fancy")
        '<span class="fancy">Hiya</span>'
        >>> t("span", "Bye", data__foo="bar")
        '<span data-foo="bar">Hiya</span>'

    Note that trailing underscores (``_``) are trimmed from attribute names and
    double underscores (``__``) are replaced with hyphens.
    """

    attrs_str = " ".join(
        name.rstrip("_").replace("__", "-") + "=" + quoteattr(value)
        for name, value in attrs.items()
    )

    if body is None:
        return f"<{tag} {attrs_str}/>"
    else:
        if "\n" in body:
            body = "\n" + indent(body, "  ").rstrip() + "\n"
        return f"<{tag}{(' ' + attrs_str).rstrip()}>{body}</{tag}>"


def render_number(number: Union[float, int, Fraction]) -> str:
    string = format_number(number)

    match = re.fullmatch(r"((?:\d+ )?)(\d+)/(\d+)", string)
    if match is not None:
        # Format fractions using fancy HTML super/subscripts
        integer, superscript, subscript = match.groups()
        superscript = t("sup", superscript)
        subscript = t("sub", subscript)
        return f"{integer}{superscript}&frasl;{subscript}"
    else:
        return string


def render_quantity(quantity: Quantity) -> str:
    if quantity.unit is None:
        return t(
            "span",
            render_number(quantity.value),
            class_="rg-quantity-unitless rg-scaled-value",
        )
    else:
        alternative_forms: List[Tuple[Union[float, int, Fraction], str]] = []

        try:
            # Present units ordered such that the current unit goes first
            # followed by all with a non-float conversion and then the
            # remaining scales.
            for scale, name in sorted(
                UNIT_SYSTEM.iter_conversions_from(quantity.unit.lower()),
                key=lambda scale_and_name: (
                    scale_and_name[0] != 1,
                    isinstance(scale_and_name[0], float),
                    scale_and_name[1],
                ),
            ):
                alternative_forms.append((quantity.value * scale, name))

            # Don't use normalised unit name for the 'native' quantity
            assert alternative_forms[0][0] == quantity.value  # Sanity check...
            alternative_forms[0] = (quantity.value, quantity.unit)
        except KeyError:
            alternative_forms.append((quantity.value, quantity.unit))

        all_forms = [
            f"{render_number(value)} {html.escape(unit)}"
            for value, unit in alternative_forms
        ]

        data_attr = (
            {"data__rg__alternative__units": json.dumps(all_forms)}
            if len(all_forms) > 1
            else {}
        )

        return t(
            "span", all_forms[0], class_="rg-quantity rg-scaled-value", **data_attr,
        )


def render_proportion(proportion: Proportion) -> str:
    if proportion.value is None:
        return t("span", "remaining", class_="rg-proportion-remainder",)
    else:
        return t(
            "span",
            render_number(proportion.value) + " &times;",
            class_="rg-proportion",
        )


def render_scaled_value_string(string: SVS) -> str:
    return string.render(
        format_number=lambda number: t(
            "span", render_number(number), class_="rg-scaled-value"
        ),
        format_string=html.escape,
    )


def render_ingredient(ingredient: Ingredient) -> str:
    quantity = (
        render_quantity(ingredient.quantity) + " "
        if ingredient.quantity is not None
        else ""
    )
    description = render_scaled_value_string(ingredient.description)
    return quantity + description


def generate_subrecipe_output_id(sub_recipe: SubRecipe, output_index: int) -> str:
    name = str(sub_recipe.output_names[output_index])
    return "sub-recipe-" + re.sub(r"[^a-zA-Z0-9._-]", "-", name).strip("-")


def render_reference(reference: Reference) -> str:
    amount: str
    if isinstance(reference.amount, Quantity):
        amount = render_quantity(reference.amount) + " "
    elif isinstance(reference.amount, Proportion):
        if reference.amount.value != 1.0:
            amount = render_proportion(reference.amount) + " "
        else:
            amount = ""
    else:
        raise NotImplementedError(type(reference.amount))

    name = render_scaled_value_string(
        reference.sub_recipe.output_names[reference.output_index]
    )

    return t(
        "a",
        amount + name,
        href="#"
        + generate_subrecipe_output_id(reference.sub_recipe, reference.output_index,),
    )


def render_step(step: Step) -> str:
    return render_scaled_value_string(step.description)


def render_sub_recipe_header(sub_recipe: SubRecipe) -> str:
    return t(
        "a",
        render_scaled_value_string(sub_recipe.output_names[0]),
        id=generate_subrecipe_output_id(sub_recipe, 0),
    )


def render_sub_recipe_outputs(sub_recipe: SubRecipe) -> str:
    return t(
        "ul",
        "\n".join(
            t(
                "li",
                t(
                    "a",
                    render_scaled_value_string(name),
                    id=generate_subrecipe_output_id(sub_recipe, index),
                ),
            )
            for index, name in enumerate(sub_recipe.output_names)
        ),
        class_="rg-sub-recipe-output-list",
    )


def render_cell(cell: Cell[RecipeTreeNode]) -> str:
    spans: MutableMapping[str, str] = {}
    if cell.columns != 1:
        spans["colspan"] = str(cell.columns)
    if cell.rows != 1:
        spans["rowspan"] = str(cell.rows)

    class_names: List[str] = []

    body: str
    if isinstance(cell.value, Ingredient):
        class_names.append("rg-ingredient")
        body = render_ingredient(cell.value)
    elif isinstance(cell.value, Reference):
        class_names.append("rg-reference")
        body = render_reference(cell.value)
    elif isinstance(cell.value, Step):
        class_names.append("rg-step")
        body = render_step(cell.value)
    elif isinstance(cell.value, SubRecipe):
        if len(cell.value.output_names) == 1:
            if cell.value.show_output_names:
                class_names.append("rg-sub-recipe-header")
            else:
                class_names.append("rg-sub-recipe-hidden-header")
            body = render_sub_recipe_header(cell.value)
        else:
            if cell.value.show_output_names:
                class_names.append("rg-sub-recipe-outputs")
            else:
                class_names.append("rg-sub-recipe-hidden-outputs")
            body = render_sub_recipe_outputs(cell.value)

    for edge in ["left", "right", "top", "bottom"]:
        border_type: BorderType = getattr(cell, f"border_{edge}")
        if border_type != BorderType.normal:
            class_names.append(f"rg-border-{edge}-{border_type.name.replace('_', '-')}")

    return t("td", body, class_=" ".join(class_names), **spans)


def render_table(table: Table[RecipeTreeNode]) -> str:
    return t(
        "table",
        "\n".join(
            t(
                "tr",
                "\n".join(
                    render_cell(cell) for cell in row_cells if isinstance(cell, Cell)
                ),
            )
            for row_cells in table.cells
        ),
        class_="rg-table",
    )
