import pytest

from pathlib import Path

from textwrap import dedent

from recipe_grid.static_site.exceptions import (
    ReadmeMissingTitleError,
    ReadmeMalformedTitleError,
    RecipeMissingTitleError,
    RecipeMissingServingsError,
    RecipeInDirectoryCompileError,
    MultipleReadmeError,
)

from recipe_grid.static_site.recipe_directory import (
    dirname_to_title,
    compile_readme_markdown,
    compile_recipe_markdown,
    RecipeDirectoryListing,
    enumerate_recipe_directory,
)


@pytest.mark.parametrize(
    "dirname, exp",
    [
        # Empty
        ("", ""),
        # Whitespace only
        (" ", ""),
        # Single word
        ("foo", "Foo"),
        ("FOO", "Foo"),
        ("123", "123"),
        # Multiple words
        ("fooBar", "Foo bar"),
        ("foo_bar", "Foo bar"),
        ("FOO_BAR", "Foo bar"),
        # With numbers
        ("foo123", "Foo 123"),
        ("FOO_123", "Foo 123"),
        ("123foo", "123 foo"),
        ("123_foo", "123 foo"),
        ("foo123bar", "Foo 123 bar"),
        ("foo2bar", "Foo 2 bar"),
        # With real spaces
        ("foo bar baz", "Foo bar baz"),
        # With excess spaces
        ("  foo    bar  ", "Foo bar"),
        # With other misc punctuation
        ("foo@bar", "Foo bar"),
    ],
)
def test_filename_to_title(dirname: str, exp: str) -> None:
    assert dirname_to_title(dirname) == exp


class TestCompileReadmeMarkdown:
    @pytest.mark.parametrize(
        "markdown",
        [
            # Empty
            "",
            # No title
            "Hello",
            # Title is not h1
            "## Hello",
            # H1 title is not first
            "## Hello\n# World",
            "Hello\n# World",
        ],
    )
    def test_no_h1_title(self, tmp_path: Path, markdown: str) -> None:
        md = tmp_path / "test.md"
        md.open("w").write(markdown)
        with pytest.raises(ReadmeMissingTitleError):
            compile_readme_markdown(md)

    def test_title_contains_html(self, tmp_path: Path) -> None:
        md = tmp_path / "test.md"
        md.open("w").write("# Hello *world*")
        with pytest.raises(ReadmeMalformedTitleError):
            compile_readme_markdown(md)

    @pytest.mark.parametrize(
        "markdown, exp_title, exp_description",
        [
            # Just title
            ("# Hello", "Hello", ""),
            # Contains HTML escapes
            ("# Foo & Bar", "Foo & Bar", ""),
            # Title and description
            ("# Hello\nWorld\n\nHooray!", "Hello", "<p>World</p>\n<p>Hooray!</p>\n"),
        ],
    )
    def test_valid(
        self, tmp_path: Path, markdown: str, exp_title: str, exp_description: str
    ) -> None:
        md = tmp_path / "test.md"
        md.open("w").write(markdown)
        title, description = compile_readme_markdown(md)
        assert title == exp_title
        assert description == description


class TestCompileRecipeMarkdown:
    def test_recipe_missing_title(self, tmp_path: Path) -> None:
        f = tmp_path / "recipe.md"
        f.open("w").write("A title-less recipe")
        with pytest.raises(RecipeMissingTitleError):
            compile_recipe_markdown(f)

        # Shouldn't crash
        compile_recipe_markdown(f, require_title=False, require_servings=False)

    def test_recipe_missing_servings(self, tmp_path: Path) -> None:
        f = tmp_path / "recipe.md"
        f.open("w").write("# A serving-less recipe")
        with pytest.raises(RecipeMissingServingsError):
            compile_recipe_markdown(f)

        # Shouldn't crash
        compile_recipe_markdown(f, require_servings=False)

    def test_recipe_syntax_error(self, tmp_path: Path) -> None:
        f = tmp_path / "recipe.md"
        f.open("w").write(
            dedent(
                """
                    # Fail for 1
                    ```recipe
                    Missing a ( closing bracket...
                    ```
                """
            )
        )
        with pytest.raises(RecipeInDirectoryCompileError):
            compile_recipe_markdown(f)

    def test_recipe_compile_error(self, tmp_path: Path) -> None:
        f = tmp_path / "recipe.md"
        f.open("w").write(
            dedent(
                """
                    # Fail for 1
                    ```recipe
                    1/2 of undefined sub recipe
                    ```
                """
            )
        )
        with pytest.raises(RecipeInDirectoryCompileError):
            compile_recipe_markdown(f)

    def test_valid(self, tmp_path: Path) -> None:
        f = tmp_path / "recipe.md"
        f.open("w").write("# A recipe for 2")
        r = compile_recipe_markdown(f)

        assert r.title == "A recipe"
        assert r.servings == 2

    def test_cache_transparency(self, tmp_path: Path) -> None:
        f = tmp_path / "recipe.md"
        f.open("w").write("# A recipe for 2")

        r1 = compile_recipe_markdown(f)
        r2 = compile_recipe_markdown(f)

        # Result from cache
        assert r2 is r1

        # Changing the file on disk should return newly compiled output
        f.open("w").write("# A different recipe for 3")
        r3 = compile_recipe_markdown(f)
        assert r3.title == "A different recipe"
        assert r3.servings == 3


class TestEnumerateRecipeDirectory:
    def test_not_exists(self, tmp_path: Path) -> None:
        path = tmp_path / "not_exists"
        with pytest.raises(NotADirectoryError):
            enumerate_recipe_directory(path)

    def test_not_a_directory(self, tmp_path: Path) -> None:
        path = tmp_path / "not_exists"
        path.open("w").write("")
        with pytest.raises(NotADirectoryError):
            enumerate_recipe_directory(path)

    def test_empty(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()
        assert enumerate_recipe_directory(empty_dir) == RecipeDirectoryListing(
            title="Empty dir",
            description_html=None,
            description_source=None,
            subdirectories=[],
            recipes=[],
        )

    @pytest.mark.parametrize(
        "readme_filename",
        ["index.md", "INDEX.md", "readme.md", "README.md"],
    )
    def test_readme(self, tmp_path: Path, readme_filename: str) -> None:
        path = tmp_path / "test_dir"
        path.mkdir()

        readme = path / readme_filename
        readme.open("w").write("# A Directory\nTa-da!")

        assert enumerate_recipe_directory(path) == RecipeDirectoryListing(
            title="A Directory",
            description_html="<p>Ta-da!</p>\n",
            description_source=readme,
            subdirectories=[],
            recipes=[],
        )

    def test_multiple_index_files(self, tmp_path: Path) -> None:
        (tmp_path / "index.md").open("w").write("# Hello")
        (tmp_path / "readme.md").open("w").write("# Hello")
        with pytest.raises(MultipleReadmeError):
            enumerate_recipe_directory(tmp_path)

    def test_recipes(self, tmp_path: Path) -> None:
        path = tmp_path / "test_dir"
        path.mkdir()

        (path / "foo.md").open("w").write("# Foo for 2")
        (path / "bar.md").open("w").write("# Bar for 3")

        d = enumerate_recipe_directory(path)

        assert len(d.recipes) == 2

        assert set(d.recipes) == {path / "foo.md", path / "bar.md"}
