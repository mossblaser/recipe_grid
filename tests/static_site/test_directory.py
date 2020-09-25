import pytest

from textwrap import dedent

from pathlib import Path

from recipe_grid.static_site.directory import (
    filename_to_title,
    compile_readme_markdown,
    RecipeDirectory,
    NotADirectoryError,
    MultipleIndexError,
    IndexMissingTitleError,
    IndexMalformedTitleError,
    RecipeMissingTitleError,
    RecipeMissingServingsError,
    RecipeInDirectoryCompileError,
)


@pytest.mark.parametrize(
    "filename, exp",
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
    ],
)
def test_filename_to_title(filename: str, exp: str) -> None:
    assert filename_to_title(filename) == exp


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
    def test_no_h1_title(self, tmp_path, markdown: str) -> None:
        md = tmp_path / "test.md"
        md.open("w").write(markdown)
        with pytest.raises(IndexMissingTitleError):
            compile_readme_markdown(md)

    def test_title_contains_html(self, tmp_path) -> None:
        md = tmp_path / "test.md"
        md.open("w").write("# Hello *world*")
        with pytest.raises(IndexMalformedTitleError):
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
        self, tmp_path, markdown: str, exp_title: str, exp_description: str
    ) -> None:
        md = tmp_path / "test.md"
        md.open("w").write(markdown)
        title, description = compile_readme_markdown(md)
        assert title == exp_title
        assert description == description


class TestRecipeDirectory:
    def test_not_exists(self, tmp_path: Path) -> None:
        path = tmp_path / "not_exists"
        with pytest.raises(NotADirectoryError):
            RecipeDirectory(path)

    def test_not_a_directory(self, tmp_path: Path) -> None:
        path = tmp_path / "not_exists"
        path.open("w").write("")
        with pytest.raises(NotADirectoryError):
            RecipeDirectory(path)

    def test_empty(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()
        d = RecipeDirectory(empty_dir)

        assert d.directory == empty_dir
        assert d.title == "Empty dir"
        assert d.description == ""
        assert d.subdirectories == {}
        assert d.recipes == {}
        assert bool(d) is False

    @pytest.mark.parametrize(
        "readme_filename", ["index.md", "INDEX.md", "readme.md", "README.md"],
    )
    def test_readme(self, tmp_path: Path, readme_filename: str) -> None:
        path = tmp_path / "test_dir"
        path.mkdir()

        readme = path / readme_filename
        readme.open("w").write("# A Directory\nTa-da!")

        d = RecipeDirectory(path)

        assert d.directory == path
        assert d.title == "A Directory"
        assert d.description == "<p>Ta-da!</p>\n"
        assert d.subdirectories == {}
        assert d.recipes == {}
        assert bool(d) is False

    def test_multiple_index_files(self, tmp_path: Path) -> None:
        (tmp_path / "index.md").open("w").write("# Hello")
        (tmp_path / "readme.md").open("w").write("# Hello")
        with pytest.raises(MultipleIndexError):
            RecipeDirectory(tmp_path)

    def test_recipes(self, tmp_path: Path) -> None:
        path = tmp_path / "test_dir"
        path.mkdir()

        (path / "foo.md").open("w").write("# Foo for 2")
        (path / "bar.md").open("w").write("# Bar for 3")

        d = RecipeDirectory(path)

        assert {p: r.title for p, r in d.recipes.items()} == {
            path / "foo.md": "Foo",
            path / "bar.md": "Bar",
        }
        assert bool(d) is True

    def test_recipe_missing_title(self, tmp_path: Path) -> None:
        path = tmp_path / "test_dir"
        path.mkdir()
        (path / "foo.md").open("w").write("A title-less recipe")
        with pytest.raises(RecipeMissingTitleError):
            RecipeDirectory(path)

    def test_recipe_missing_servings(self, tmp_path: Path) -> None:
        path = tmp_path / "test_dir"
        path.mkdir()
        (path / "foo.md").open("w").write("# Recipe for unknown number")
        with pytest.raises(RecipeMissingServingsError):
            RecipeDirectory(path)

    def test_recipe_syntax_error(self, tmp_path: Path) -> None:
        (tmp_path / "foo.md").open("w").write(
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
            RecipeDirectory(tmp_path)

    def test_recipe_compile_error(self, tmp_path: Path) -> None:
        (tmp_path / "foo.md").open("w").write(
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
            RecipeDirectory(tmp_path)

    def test_recursion(self, tmp_path: Path) -> None:
        path = tmp_path / "test_dir"
        path.mkdir(parents=True)
        (path / "child").mkdir()
        (path / "empty" / "grandchild").mkdir(parents=True)
        (path / "really_empty").mkdir()

        (path / "foo.md").open("w").write("# Foo for 2")
        (path / "child" / "bar.md").open("w").write("# Bar for 3")
        (path / "empty" / "grandchild" / "baz.md").open("w").write("# Baz for 4")
        (path / "really_empty" / "index.md").open("w").write("# No recipes here...")

        d = RecipeDirectory(path)

        assert set(d.subdirectories) == {
            path / "child",
            path / "empty",
            # NB: really_empty not listed due to lacking any recipes (even
            # though it has an index file)
        }

        assert set(d.recipes) == {path / "foo.md"}

        assert set(d.subdirectories[path / "child"].recipes) == {
            path / "child" / "bar.md"
        }

        assert d.subdirectories[path / "empty"].recipes == {}

        assert set(
            d.subdirectories[path / "empty"]
            .subdirectories[path / "empty" / "grandchild"]
            .recipes
        ) == {path / "empty" / "grandchild" / "baz.md"}
