import pytest

from typing import Optional

from textwrap import dedent

from peggie import ParseError

from fractions import Fraction

from recipe_grid.recipe import (
    Recipe,
    Step,
    Ingredient,
    Reference,
    SubRecipe,
    Quantity,
)

from recipe_grid.scaled_value_string import ScaledValueString as SVS

from recipe_grid.markdown import (
    generate_placeholder,
    compile_markdown,
)


def test_generate_placeholder() -> None:
    assert len(set(generate_placeholder() for _ in range(100))) == 100


class TestRenderMarkdown:
    def test_no_recipes(self) -> None:
        assert compile_markdown("").render() == ""
        assert compile_markdown("Hello").render() == "<p>Hello</p>\n"

    @pytest.mark.parametrize(
        "markdown, exp, exp10,",
        [
            # Decimals
            (
                "Hello {foo 123 bar}",
                '<p>Hello foo <span class="rg-scaled-value">123</span> bar</p>\n',
                '<p>Hello foo <span class="rg-scaled-value">1230</span> bar</p>\n',
            ),
            (
                "Hello {foo 1.2345 bar}",
                '<p>Hello foo <span class="rg-scaled-value">1.23</span> bar</p>\n',
                '<p>Hello foo <span class="rg-scaled-value">12.3</span> bar</p>\n',
            ),
            # Fractions
            (
                "Hello {foo 1/3 bar}",
                (
                    '<p>Hello foo <span class="rg-scaled-value">'
                    "<sup>1</sup>&frasl;<sub>3</sub>"
                    "</span> bar</p>\n"
                ),
                (
                    '<p>Hello foo <span class="rg-scaled-value">'
                    "3 <sup>1</sup>&frasl;<sub>3</sub>"
                    "</span> bar</p>\n"
                ),
            ),
            (
                "Hello {foo 1 2/3 bar}",
                (
                    '<p>Hello foo <span class="rg-scaled-value">'
                    "1 <sup>2</sup>&frasl;<sub>3</sub>"
                    "</span> bar</p>\n"
                ),
                (
                    '<p>Hello foo <span class="rg-scaled-value">'
                    "16 <sup>2</sup>&frasl;<sub>3</sub>"
                    "</span> bar</p>\n"
                ),
            ),
            # Escape sequences
            (
                r"Hello \{ and \}.",
                "<p>Hello { and }.</p>\n",
                "<p>Hello { and }.</p>\n",
            ),
            # Contains chars requiring HTML escapes
            (
                "Hello {&} goodbye.",
                "<p>Hello &amp; goodbye.</p>\n",
                "<p>Hello &amp; goodbye.</p>\n",
            ),
            # Missing close bracket should result in nothing being matched
            (
                "Hello {& goodbye.",
                "<p>Hello {&amp; goodbye.</p>\n",
                "<p>Hello {&amp; goodbye.</p>\n",
            ),
            # Integration with other markdown features
            (
                "## Italic *title {with 123}*",
                '<h2>Italic <em>title with <span class="rg-scaled-value">123</span></em></h2>\n',
                '<h2>Italic <em>title with <span class="rg-scaled-value">1230</span></em></h2>\n',
            ),
        ],
    )
    def test_scaled_value_expr(self, markdown: str, exp: str, exp10: str) -> None:
        compiled = compile_markdown(markdown)
        assert compiled.render(1) == exp
        assert compiled.render(10) == exp10

    def test_scaled_value_expr_integers_stay_as_ints(self) -> None:
        compiled = compile_markdown("{5}")
        assert compiled.render(Fraction(1, 3)) == (
            '<p><span class="rg-scaled-value">1 <sup>2</sup>&frasl;<sub>3</sub></span></p>\n'
        )

        compiled = compile_markdown("{5.0}")
        assert compiled.render(Fraction(1, 3)) == (
            '<p><span class="rg-scaled-value">1.67</span></p>\n'
        )

    @pytest.mark.parametrize(
        "source",
        [
            # Indented block
            """
                A recipe for 2
                ==============

                    100g spam
                    2 eggs
                    fry(spam, eggs)

                Ta-da!
            """,
            # Fenced block
            """
                A recipe for 2
                ==============

                ~~~recipe
                100g spam
                2 eggs
                fry(spam, eggs)
                ~~~

                Ta-da!
            """,
            # Fenced block (new recipe)
            """
                A recipe for 2
                ==============

                ~~~new-recipe
                100g spam
                2 eggs
                fry(spam, eggs)
                ~~~

                Ta-da!
            """,
        ],
    )
    def test_recipe_code_blocks_and_scaled_rendering(self, source: str) -> None:
        compiled = compile_markdown(dedent(source).strip())
        assert compiled.title == "A recipe"
        assert compiled.servings == 2
        assert compiled.recipes == [
            [
                Recipe(
                    (
                        Step(
                            SVS("fry"),
                            (
                                Ingredient(SVS("spam"), Quantity(100, "g")),
                                Ingredient(SVS("eggs"), Quantity(2)),
                            ),
                        ),
                    )
                ),
            ]
        ]
        assert (
            compiled.render(2)
            == dedent(
                """
                <header><h1 class="rg-title-scalable">A recipe <span class="rg-serving-count">for <span class="rg-scaled-value">4</span></span></h1><p>Rescaled from <span class="rg-original-servings">2 servings</span>.</p></header>
                <div class="rg-recipe-block">
                  <table class="rg-table">
                    <tr>
                      <td class="rg-ingredient rg-border-left-sub-recipe rg-border-top-sub-recipe">
                        <span class="rg-quantity-with-conversions rg-scaled-value" tabindex="0">
                          200g<ul class="rg-quantity-conversions">
                            <li><sup>1</sup>&frasl;<sub>5</sub>kg</li>
                            <li>0.441lb</li>
                            <li>7.05oz</li>
                          </ul>
                        </span> spam
                      </td>
                      <td class="rg-step rg-border-right-sub-recipe rg-border-top-sub-recipe rg-border-bottom-sub-recipe" rowspan="2">fry</td>
                    </tr>
                    <tr><td class="rg-ingredient rg-border-left-sub-recipe rg-border-bottom-sub-recipe"><span class="rg-quantity-unitless rg-scaled-value">4</span> eggs</td></tr>
                  </table>
                </div><p>Ta-da!</p>
            """  # noqa: E501
            ).lstrip()
        )

    def test_non_recipe_fenced_block(self) -> None:
        assert (
            compile_markdown("~~~\nfoo\n~~~").render()
            == "<pre><code>foo\n</code></pre>\n"
        )

    def test_recipes_split_across_blocks(self) -> None:
        compiled = compile_markdown(
            dedent(
                """
                A recipe in two parts. Part one:

                    sauce = boil down(tomatoes, water)

                Part two:

                    pour over(pasta, sauce)
                """
            ).strip()
        )

        sr = SubRecipe(
            Step(
                SVS("boil down"),
                (
                    Ingredient(SVS("tomatoes")),
                    Ingredient(SVS("water")),
                ),
            ),
            (SVS("sauce"),),
        )
        r1 = Recipe((sr,))
        r2 = Recipe(
            (
                Step(
                    SVS("pour over"),
                    (
                        Ingredient(SVS("pasta")),
                        Reference(sr),
                    ),
                ),
            ),
            follows=r1,
        )

        assert compiled.recipes == [[r1, r2]]

    def test_separate_recipes(self) -> None:
        compiled = compile_markdown(
            dedent(
                """
                Fried egg:

                ```recipe
                1 egg
                ```

                ```recipe
                fry(egg)
                ```

                Boiled egg:

                ```new-recipe
                2 egg
                ```

                ```recipe
                boil(egg)
                ```
                """
            ).strip()
        )

        e1 = SubRecipe(
            Ingredient(SVS("egg"), Quantity(1)),
            (SVS("egg"),),
            show_output_names=False,
        )
        r1 = Recipe((e1,))
        r2 = Recipe((Step(SVS("fry"), (Reference(e1),)),), follows=r1)

        e2 = SubRecipe(
            Ingredient(SVS("egg"), Quantity(2)),
            (SVS("egg"),),
            show_output_names=False,
        )
        r3 = Recipe((e2,))
        r4 = Recipe((Step(SVS("boil"), (Reference(e2),)),), follows=r3)

        assert compiled.recipes == [[r1, r2], [r3, r4]]

        # Check anchor IDs are unique too
        html = compiled.render()
        assert 'id="recipe-egg"' in html
        assert 'href="#recipe-egg"' in html
        assert 'id="recipe2-egg"' in html
        assert 'href="#recipe2-egg"' in html

    @pytest.mark.parametrize(
        "source",
        [
            # Fenced block (NB syntax error on line 5)
            """
                Hello
                =====

                ~~~recipe
                foo = fried()
                ~~~
            """,
            # Indented block (NB syntax error also at line 5)
            """
                Hello
                =====


                    foo = fried()
                ~~~
            """,
        ],
    )
    def test_error_message_line_numbers(self, source: str) -> None:
        with pytest.raises(ParseError) as exc_info:
            compile_markdown(dedent(source).strip())

        assert (
            str(exc_info.value)
            == dedent(
                """
                At line 5 column 13:
                    foo = fried()
                                ^
                Expected <action> or <ingredient> or <quantity>
            """
            ).strip()
        )

    @pytest.mark.parametrize(
        "source, exp_title, exp_servings, exp_html, exp_html_10",
        [
            # No title
            (
                "Hello",
                None,
                None,
                "<p>Hello</p>\n",
                "<p>Hello</p>\n",
            ),
            # First title is not a h1
            (
                "## Hello\n# World",
                None,
                None,
                "<h2>Hello</h2>\n<h1>World</h1>\n",
                "<h2>Hello</h2>\n<h1>World</h1>\n",
            ),
            # Title contains HTML
            (
                "# <span>Hi</span>",
                None,
                None,
                "<h1><span>Hi</span></h1>\n",
                "<h1><span>Hi</span></h1>\n",
            ),
            # Title contains scaled value
            (
                "# {123}",
                None,
                None,
                '<h1><span class="rg-scaled-value">123</span></h1>\n',
                '<h1><span class="rg-scaled-value">1230</span></h1>\n',
            ),
            # Title with no servings count
            (
                "# Food & drink",
                "Food & drink",
                None,
                '<header><h1 class="rg-title-unscalable">Food &amp; drink</h1></header>\n',
                (
                    '<header><h1 class="rg-title-unscalable">Food &amp; drink</h1>'
                    '<p>Scaled <span class="rg-scaling-factor">10&times;</span>'
                    "</p></header>\n"
                ),
            ),
            # Title with serving count
            (
                "# Food & drink for 3",
                "Food & drink",
                3,
                (
                    '<header><h1 class="rg-title-scalable">Food &amp; drink '
                    '<span class="rg-serving-count">for '
                    '<span class="rg-scaled-value">3</span></span></h1></header>\n'
                ),
                (
                    '<header><h1 class="rg-title-scalable">Food &amp; drink '
                    '<span class="rg-serving-count">for '
                    '<span class="rg-scaled-value">30</span></span></h1>'
                    '<p>Rescaled from <span class="rg-original-servings">3 '
                    "servings</span>.</p></header>\n"
                ),
            ),
            # Title with serving count with longer preposition
            (
                "# Food & drink to serve 3",
                "Food & drink",
                3,
                (
                    '<header><h1 class="rg-title-scalable">Food &amp; drink '
                    '<span class="rg-serving-count">to serve '
                    '<span class="rg-scaled-value">3</span></span></h1></header>\n'
                ),
                (
                    '<header><h1 class="rg-title-scalable">Food &amp; drink '
                    '<span class="rg-serving-count">to serve '
                    '<span class="rg-scaled-value">30</span></span></h1>'
                    '<p>Rescaled from <span class="rg-original-servings">3 '
                    "servings</span>.</p></header>\n"
                ),
            ),
            # Title with longer preposition if only for the lack of a space
            (
                "# Risotto serves 3",
                "Risotto",
                3,
                (
                    '<header><h1 class="rg-title-scalable">Risotto '
                    '<span class="rg-serving-count">serves '
                    '<span class="rg-scaled-value">3</span></span></h1></header>\n'
                ),
                (
                    '<header><h1 class="rg-title-scalable">Risotto '
                    '<span class="rg-serving-count">serves '
                    '<span class="rg-scaled-value">30</span></span></h1>'
                    '<p>Rescaled from <span class="rg-original-servings">3 '
                    "servings</span>.</p></header>\n"
                ),
            ),
            # Original serving count was 1
            (
                "# Food & drink for 1",
                "Food & drink",
                1,
                (
                    '<header><h1 class="rg-title-scalable">Food &amp; drink '
                    '<span class="rg-serving-count">for '
                    '<span class="rg-scaled-value">1</span></span></h1></header>\n'
                ),
                (
                    '<header><h1 class="rg-title-scalable">Food &amp; drink '
                    '<span class="rg-serving-count">for '
                    '<span class="rg-scaled-value">10</span></span></h1>'
                    '<p>Rescaled from <span class="rg-original-servings">1 '
                    "serving</span>.</p></header>\n"
                ),
            ),
        ],
    )
    def test_title_parsing(
        self,
        source: str,
        exp_title: Optional[str],
        exp_servings: Optional[int],
        exp_html: str,
        exp_html_10: str,
    ) -> None:
        compiled = compile_markdown(dedent(source).strip())
        assert compiled.title == exp_title
        assert compiled.servings == exp_servings
        assert compiled.render(1) == exp_html
        assert compiled.render(10) == exp_html_10
