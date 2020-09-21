import pytest

from textwrap import dedent

from peggie import ParseError

from recipe_grid.markdown.html import (
    generate_random_string,
    render_markdown,
)


def test_generate_random_string() -> None:
    assert len(set(generate_random_string() for _ in range(100))) == 100


class TestRenderMarkdown:
    def test_no_recipes(self) -> None:
        assert render_markdown("") == ""
        assert render_markdown("Hello\n=====") == "<h1>Hello</h1>\n"

    def test_non_recipe_fenced_block(self) -> None:
        assert render_markdown("~~~\nfoo\n~~~") == "<pre><code>foo\n</code></pre>\n"

    @pytest.mark.parametrize(
        "source",
        [
            # Indented block
            """
                Hello
                =====

                A recipe:

                    100g spam
                    2 eggs
                    fry(spam, eggs)

                Ta-da!
            """,
            # Fenced block
            """
                Hello
                =====

                A recipe:

                ~~~recipe
                100g spam
                2 eggs
                fry(spam, eggs)
                ~~~

                Ta-da!
            """,
            # Fenced block (new recipe)
            """
                Hello
                =====

                A recipe:

                ~~~new-recipe
                100g spam
                2 eggs
                fry(spam, eggs)
                ~~~

                Ta-da!
            """,
        ],
    )
    def test_single_recipe(self, source: str) -> None:
        assert (
            render_markdown(dedent(source).strip())
            == dedent(
                """
                <h1>Hello</h1>
                <p>A recipe:</p>
                <div class="rg-recipe">
                  <table class="rg-table">
                    <tr>
                      <td class="rg-ingredient"><span class="rg-quantity rg-scaled-value" data-rg-alternative-units='["100g", "0.1kg", "0.22lb", "3.53oz"]'>100g</span> spam</td>
                      <td class="rg-step" rowspan="2">fry</td>
                    </tr>
                    <tr><td class="rg-ingredient"><span class="rg-quantity-unitless rg-scaled-value">2</span> eggs</td></tr>
                  </table>
                </div><p>Ta-da!</p>
            """  # noqa: E501
            ).lstrip()
        )

    @pytest.mark.parametrize(
        "source",
        [
            # Indented block
            """
                Hello
                =====

                The ingredients:

                    100g spam
                    2 eggs

                The recipe:

                    fry(spam, eggs)

                Ta-da!
            """,
            # Fenced block
            """
                Hello
                =====

                The ingredients:

                ~~~recipe
                100g spam
                2 eggs
                ~~~

                The recipe:

                ~~~recipe
                fry(spam, eggs)
                ~~~

                Ta-da!
            """,
        ],
    )
    def test_recipe_in_two_blocks(self, source: str) -> None:
        # NB: Two sections with cross-references between them (i.e. they've
        # been compiled together as a single recipe split into multiple
        # blocks).
        assert (
            render_markdown(dedent(source).strip())
            == dedent(
                """
                <h1>Hello</h1>
                <p>The ingredients:</p>
                <div class="rg-recipe">
                  <table class="rg-table">
                    <tr><td class="rg-sub-recipe-hidden-header rg-border-left-sub-recipe rg-border-right-sub-recipe rg-border-top-sub-recipe"><a id="sub-recipe-spam">spam</a></td></tr>
                    <tr><td class="rg-ingredient rg-border-left-sub-recipe rg-border-right-sub-recipe rg-border-bottom-sub-recipe"><span class="rg-quantity rg-scaled-value" data-rg-alternative-units='["100g", "0.1kg", "0.22lb", "3.53oz"]'>100g</span> spam</td></tr>
                  </table>
                  <table class="rg-table">
                    <tr><td class="rg-sub-recipe-hidden-header rg-border-left-sub-recipe rg-border-right-sub-recipe rg-border-top-sub-recipe"><a id="sub-recipe-eggs">eggs</a></td></tr>
                    <tr><td class="rg-ingredient rg-border-left-sub-recipe rg-border-right-sub-recipe rg-border-bottom-sub-recipe"><span class="rg-quantity-unitless rg-scaled-value">2</span> eggs</td></tr>
                  </table>
                </div><p>The recipe:</p>
                <div class="rg-recipe">
                  <table class="rg-table">
                    <tr>
                      <td class="rg-reference"><a href="#sub-recipe-spam">spam</a></td>
                      <td class="rg-step" rowspan="2">fry</td>
                    </tr>
                    <tr><td class="rg-reference"><a href="#sub-recipe-eggs">eggs</a></td></tr>
                  </table>
                </div><p>Ta-da!</p>
            """  # noqa: E501
            ).lstrip()
        )

    def test_new_recipe_block(self) -> None:
        # NB: The new-recipe block has its own namespace and doesn't reference
        # the previous block (This would be a compile error without the
        # 'new-recipe').
        assert (
            render_markdown(
                dedent(
                    """
                    Hello
                    =====

                    First recipe:

                    ~~~recipe
                    eggs = 2 eggs, boiled
                    ~~~

                    Second recipe:

                    ~~~new-recipe
                    eggs = 3 eggs, fried
                    ~~~

                    Ta-da!
                """
                ).strip()
            )
            == dedent(
                """
                <h1>Hello</h1>
                <p>First recipe:</p>
                <div class="rg-recipe">
                  <table class="rg-table">
                    <tr><td class="rg-sub-recipe-header rg-border-left-sub-recipe rg-border-right-sub-recipe rg-border-top-sub-recipe" colspan="2"><a id="sub-recipe-eggs">eggs</a></td></tr>
                    <tr>
                      <td class="rg-ingredient rg-border-left-sub-recipe rg-border-bottom-sub-recipe"><span class="rg-quantity-unitless rg-scaled-value">2</span> eggs</td>
                      <td class="rg-step rg-border-right-sub-recipe rg-border-bottom-sub-recipe">boiled</td>
                    </tr>
                  </table>
                </div><p>Second recipe:</p>
                <div class="rg-recipe">
                  <table class="rg-table">
                    <tr><td class="rg-sub-recipe-header rg-border-left-sub-recipe rg-border-right-sub-recipe rg-border-top-sub-recipe" colspan="2"><a id="sub-recipe-eggs">eggs</a></td></tr>
                    <tr>
                      <td class="rg-ingredient rg-border-left-sub-recipe rg-border-bottom-sub-recipe"><span class="rg-quantity-unitless rg-scaled-value">3</span> eggs</td>
                      <td class="rg-step rg-border-right-sub-recipe rg-border-bottom-sub-recipe">fried</td>
                    </tr>
                  </table>
                </div><p>Ta-da!</p>
            """  # noqa: E501
            ).lstrip()
        )

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
            render_markdown(dedent(source).strip())

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
