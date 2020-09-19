import pytest

from typing import Union

from fractions import Fraction

from recipe_grid.scaled_value_string import ScaledValueString as SVS

from recipe_grid.renderer.table import Table, Cell, BorderType

from recipe_grid.recipe import (
    Quantity,
    Proportion,
    Ingredient,
    SubRecipe,
    Reference,
    Step,
)

from recipe_grid.renderer.html import (
    t,
    render_number,
    render_quantity,
    render_proportion,
    render_scaled_value_string,
    render_ingredient,
    generate_subrecipe_output_id,
    render_reference,
    render_step,
    render_sub_recipe_header,
    render_sub_recipe_outputs,
    render_cell,
    render_table,
)


class TestT:
    def test_minimal_tag(self) -> None:
        assert t("foo") == "<foo />"

    def test_no_child_with_attrs(self) -> None:
        assert t("foo", bar="baz") == '<foo bar="baz"/>'
        assert t("foo", bar="baz", quo="qux") == '<foo bar="baz" quo="qux"/>'

    def test_underscore_postfix_removal(self) -> None:
        assert t("foo", class_="baz") == '<foo class="baz"/>'

    def test_dunderscore_to_hyphen_substitution(self) -> None:
        assert t("foo", data__foo="bar") == '<foo data-foo="bar"/>'

    def test_empty_body(self) -> None:
        assert t("foo", "") == "<foo></foo>"

    def test_with_body_and_attrs(self) -> None:
        assert t("foo", "", bar="baz") == '<foo bar="baz"></foo>'
        assert t("foo", "", bar="baz", quo="qux") == '<foo bar="baz" quo="qux"></foo>'

    def test_single_line_body(self) -> None:
        assert t("foo", "bar") == "<foo>bar</foo>"

    def test_single_line_body_with_trailing_newline(self) -> None:
        assert t("foo", "bar\n") == "<foo>\n  bar\n</foo>"

    def test_multi_line_body(self) -> None:
        assert t("foo", "bar\nbaz") == "<foo>\n  bar\n  baz\n</foo>"

    def test_escape_attr_values(self) -> None:
        assert (
            t("foo", bar="in 'quotes\" here") == '<foo bar="in \'quotes&quot; here"/>'
        )


@pytest.mark.parametrize(
    "number, exp",
    [
        # Integer
        (123, "123"),
        # Float
        (1.23456, "1.23"),
        # Fraction
        (Fraction(2, 3), "<sup>2</sup>&frasl;<sub>3</sub>"),
        # Improper fraction
        (Fraction(5, 3), "1 <sup>2</sup>&frasl;<sub>3</sub>"),
    ],
)
def test_render_number(number: Union[float, int, Fraction], exp: str) -> None:
    assert render_number(number) == exp


@pytest.mark.parametrize(
    "quantity, exp",
    [
        # Unitless
        (
            Quantity(123),
            '<span class="rg-quantity-unitless rg-scaled-value">123</span>',
        ),
        # Custom (unknown) unit with HTML char in
        (
            Quantity(123, "<foo>"),
            '<span class="rg-quantity rg-scaled-value">123 &lt;foo&gt;</span>',
        ),
        # Known unit (with non normative name given and with fractional and
        # floating point conversions).
        (
            Quantity(Fraction(1, 2), "Kilos"),
            (
                "<span "
                'class="rg-quantity rg-scaled-value" '
                "data-rg-alternative-units='["
                '"&lt;sup&gt;1&lt;/sup&gt;&amp;frasl;&lt;sub&gt;2&lt;/sub&gt; Kilos", '
                '"500 g", '
                '"1.1 lb", '
                '"17.6 oz"'
                "]'"
                ">"
                "<sup>1</sup>&frasl;<sub>2</sub> Kilos"
                "</span>"
            ),
        ),
    ],
)
def test_render_quantity(quantity: Quantity, exp: str) -> None:
    assert render_quantity(quantity) == exp


@pytest.mark.parametrize(
    "proportion, exp",
    [
        # Remainder
        (Proportion(None), '<span class="rg-proportion-remainder">remaining</span>'),
        # Quantity
        (Proportion(0.2), '<span class="rg-proportion">0.2 &times;</span>'),
    ],
)
def test_render_proportion(proportion: Proportion, exp: str) -> None:
    assert render_proportion(proportion) == exp


@pytest.mark.parametrize(
    "string, exp",
    [
        # Pure string
        (SVS("Hello"), "Hello"),
        # HTML special chars in string
        (SVS("<Hello>"), "&lt;Hello&gt;"),
        # Scaled values formatted and spanned
        (
            SVS([1.2345, " < ", Fraction(5, 3)]),
            (
                '<span class="rg-scaled-value">1.23</span>'
                " &lt; "
                '<span class="rg-scaled-value">1 <sup>2</sup>&frasl;<sub>3</sub></span>'
            ),
        ),
    ],
)
def test_render_scaled_value_string(string: SVS, exp: str) -> None:
    assert render_scaled_value_string(string) == exp


@pytest.mark.parametrize(
    "ingredient, exp",
    [
        # Quantity-less
        (Ingredient(SVS("Air")), "Air"),
        # With quantity
        (
            Ingredient(SVS("apples"), Quantity(2)),
            '<span class="rg-quantity-unitless rg-scaled-value">2</span> apples',
        ),
    ],
)
def test_render_ingredient(ingredient: Ingredient, exp: str) -> None:
    assert render_ingredient(ingredient) == exp


def test_generate_subrecipe_output_id() -> None:
    sub_recipe = SubRecipe(
        Ingredient(SVS("spam")), (SVS("foo"), SVS(["foo bar ", 123, " baz?"])),
    )
    assert generate_subrecipe_output_id(sub_recipe, 0) == "sub-recipe-foo"
    assert generate_subrecipe_output_id(sub_recipe, 1) == "sub-recipe-foo-bar-123-baz"


@pytest.mark.parametrize(
    "reference, exp",
    [
        # No amount (consumes whole thing)
        (
            Reference(
                SubRecipe(Ingredient(SVS("spam")), (SVS("foo"),)), 0, Proportion(1)
            ),
            '<a href="#sub-recipe-foo">foo</a>',
        ),
        # Non-whole proportion
        (
            Reference(
                SubRecipe(Ingredient(SVS("spam")), (SVS("foo"),)), 0, Proportion(None)
            ),
            (
                '<a href="#sub-recipe-foo">'
                '<span class="rg-proportion-remainder">remaining</span> foo'
                "</a>"
            ),
        ),
        (
            Reference(
                SubRecipe(Ingredient(SVS("spam")), (SVS("foo"),)), 0, Proportion(0.5)
            ),
            '<a href="#sub-recipe-foo"><span class="rg-proportion">0.5 &times;</span> foo</a>',
        ),
        # Quantity
        (
            Reference(
                SubRecipe(Ingredient(SVS("spam")), (SVS("foo"),)), 0, Quantity(2)
            ),
            (
                '<a href="#sub-recipe-foo">'
                '<span class="rg-quantity-unitless rg-scaled-value">2</span> foo'
                "</a>"
            ),
        ),
    ],
)
def test_render_reference(reference: Reference, exp: str) -> None:
    assert render_reference(reference) == exp


def test_render_step() -> None:
    assert render_step(Step(SVS("fry"), (Ingredient(SVS("spam")),))) == "fry"


def test_render_sub_recipe_header() -> None:
    assert (
        render_sub_recipe_header(SubRecipe(Ingredient(SVS("spam")), (SVS("foo"),)))
        == '<a id="sub-recipe-foo">foo</a>'
    )


def test_render_sub_recipe_outputs() -> None:
    assert render_sub_recipe_outputs(
        SubRecipe(Ingredient(SVS("spam")), (SVS("foo"), SVS("bar"), SVS("baz")),)
    ) == (
        '<ul class="rg-sub-recipe-output-list">\n'
        '  <li><a id="sub-recipe-foo">foo</a></li>\n'
        '  <li><a id="sub-recipe-bar">bar</a></li>\n'
        '  <li><a id="sub-recipe-baz">baz</a></li>\n'
        "</ul>"
    )


class TestRenderCell:
    def test_ingredient(self) -> None:
        assert (
            render_cell(Cell(Ingredient(SVS("spam"))))
            == '<td class="rg-ingredient">spam</td>'
        )

    def test_reference(self) -> None:
        assert (
            render_cell(
                Cell(Reference(SubRecipe(Ingredient(SVS("spam")), (SVS("foo"),)), 0))
            )
            == '<td class="rg-reference"><a href="#sub-recipe-foo">foo</a></td>'
        )

    def test_step(self) -> None:
        assert (
            render_cell(Cell(Step(SVS("fry"), (Ingredient(SVS("spam")),))))
            == '<td class="rg-step">fry</td>'
        )

    def test_subrecipe_header_visible(self) -> None:
        assert (
            render_cell(Cell(SubRecipe(Ingredient(SVS("spam")), (SVS("foo"),))))
            == '<td class="rg-sub-recipe-header"><a id="sub-recipe-foo">foo</a></td>'
        )

    def test_subrecipe_header_hidden(self) -> None:
        assert (
            render_cell(
                Cell(
                    SubRecipe(
                        Ingredient(SVS("spam")), (SVS("foo"),), show_output_names=False
                    )
                )
            )
            == '<td class="rg-sub-recipe-hidden-header"><a id="sub-recipe-foo">foo</a></td>'
        )

    def test_subrecipe_outputs_visible(self) -> None:
        assert render_cell(
            Cell(SubRecipe(Ingredient(SVS("spam")), (SVS("foo"), SVS("bar"))))
        ) == (
            '<td class="rg-sub-recipe-outputs">\n'
            '  <ul class="rg-sub-recipe-output-list">\n'
            '    <li><a id="sub-recipe-foo">foo</a></li>\n'
            '    <li><a id="sub-recipe-bar">bar</a></li>\n'
            "  </ul>\n"
            "</td>"
        )

    def test_subrecipe_outputs_hidden(self) -> None:
        assert render_cell(
            Cell(
                SubRecipe(
                    Ingredient(SVS("spam")),
                    (SVS("foo"), SVS("bar")),
                    show_output_names=False,
                )
            )
        ) == (
            '<td class="rg-sub-recipe-hidden-outputs">\n'
            '  <ul class="rg-sub-recipe-output-list">\n'
            '    <li><a id="sub-recipe-foo">foo</a></li>\n'
            '    <li><a id="sub-recipe-bar">bar</a></li>\n'
            "  </ul>\n"
            "</td>"
        )

    def test_colspan(self) -> None:
        assert (
            render_cell(Cell(Ingredient(SVS("spam")), columns=3,),)
            == '<td class="rg-ingredient" colspan="3">spam</td>'
        )

    def test_rowspan(self) -> None:
        assert (
            render_cell(Cell(Step(SVS("fry"), (Ingredient(SVS("spam")),)), rows=3,),)
            == '<td class="rg-step" rowspan="3">fry</td>'
        )

    def test_edges(self) -> None:
        assert render_cell(
            Cell(
                Ingredient(SVS("spam")),
                border_top=BorderType.sub_recipe,
                border_left=BorderType.none,
                border_bottom=BorderType.sub_recipe,
                border_right=BorderType.none,
            ),
        ) == (
            '<td class="'
            "rg-ingredient "
            "rg-border-left-none "
            "rg-border-right-none "
            "rg-border-top-sub-recipe "
            "rg-border-bottom-sub-recipe"
            '">spam</td>'
        )


def test_render_table() -> None:
    assert render_table(
        Table.from_dict(
            {
                (0, 0): Cell(Ingredient(SVS("spam"))),
                (1, 0): Cell(Ingredient(SVS("eggs"))),
                (0, 1): Cell(
                    Step(
                        SVS("fry"), (Ingredient(SVS("spam")), Ingredient(SVS("eggs")))
                    ),
                    rows=2,
                ),
            }
        )
    ) == (
        '<table class="rg-table">\n'
        "  <tr>\n"
        '    <td class="rg-ingredient">spam</td>\n'
        '    <td class="rg-step" rowspan="2">fry</td>\n'
        "  </tr>\n"
        '  <tr><td class="rg-ingredient">eggs</td></tr>\n'
        "</table>"
    )
