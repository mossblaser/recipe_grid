import pytest

from textwrap import dedent

from recipe_grid.markdown.extract import extract_recipe_sources_from_markdown


class TestExtractRecipeSourcesFromMarkdown:
    def test_no_recipes(self) -> None:
        assert extract_recipe_sources_from_markdown("") == []
        assert extract_recipe_sources_from_markdown("Hello") == []

    def test_inline_code_blocks(self) -> None:
        assert extract_recipe_sources_from_markdown("`foo`") == []
        assert extract_recipe_sources_from_markdown("~~~foo~~~") == []

    def test_non_recipe_fenced_block(self) -> None:
        assert extract_recipe_sources_from_markdown("~~~\nfoo\n~~~") == []

    def test_single_recipe_indented(self) -> None:
        assert extract_recipe_sources_from_markdown("    fry(eggs)\n") == [
            ["fry(eggs)\n"],
        ]

    def test_single_recipe_fenced(self) -> None:
        assert extract_recipe_sources_from_markdown("~~~recipe\nfry(eggs)\n~~~") == [
            ["\nfry(eggs)\n"],
        ]

    def test_line_number_compensation(self) -> None:
        assert (
            extract_recipe_sources_from_markdown(
                dedent(
                    """
                    First recipe block starting on line 3:

                        foo

                    Second recipe block starting on line 8:

                    ```recipe
                    bar
                    ```
                """
                ).strip()
            )
            == [["\n\nfoo\n", "\n\n\n\n\n\n\nbar\n"]]
        )

    @pytest.mark.parametrize("first_recipe_lang", ["recipe", "new-recipe"])
    def test_multiple_recipe_scopes(self, first_recipe_lang: str) -> None:
        assert (
            extract_recipe_sources_from_markdown(
                dedent(
                    f"""
                    ```{first_recipe_lang}
                    foo
                    ```
                    ```recipe
                    bar
                    ```
                    ```new-recipe
                    baz
                    ```
                    ```new-recipe
                    qux
                    ```
                    ```recipe
                    quo
                    ```
                """
                ).strip()
            )
            == [
                ["\nfoo\n", "\n\n\n\nbar\n"],
                ["\n\n\n\n\n\n\nbaz\n"],
                ["\n\n\n\n\n\n\n\n\n\nqux\n", "\n\n\n\n\n\n\n\n\n\n\n\n\nquo\n"],
            ]
        )

    def test_dont_crash_on_invalid_recipe_syntax(self) -> None:
        assert extract_recipe_sources_from_markdown("    foo =\n") == [
            ["foo =\n"],
        ]
