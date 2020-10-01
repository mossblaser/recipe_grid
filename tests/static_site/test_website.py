import pytest

from typing import Callable, Mapping, MutableMapping

import shutil

from pathlib import Path

from urllib.parse import urlsplit, unquote

import lxml.html  # type: ignore

from recipe_grid.renderer.html import t

from recipe_grid.static_site.exceptions import (
    MaxServingsLowerThanLargestRecipeError,
    LinkToExternalFileError,
)

from recipe_grid.static_site.html_postprocessing import postprocess_html

from recipe_grid.static_site.website import (
    HomePage,
    generate_static_site,
)


@pytest.fixture
def input_path(tmp_path: Path) -> Path:
    return tmp_path / "input"


@pytest.fixture
def output_path(tmp_path: Path) -> Path:
    return tmp_path / "output"


MakeDirectoryFn = Callable[[Mapping[str, str]], Path]


@pytest.fixture
def make_directory(input_path: Path) -> MakeDirectoryFn:
    """
    Text fixture which resolves to a function which takes a filename: content
    dictionary and returns a path to the generated directory.
    """
    shutil.rmtree(input_path, ignore_errors=True)
    input_path.mkdir()

    def make_directory(files: Mapping[str, str] = {}) -> Path:
        for filename, content in files.items():
            path = input_path / Path(filename)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w") as f:
                f.write(content)

        return input_path

    return make_directory


class TestPage:
    def test_get_breadcrumbs(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory(
                {
                    "README.md": "# A recipe website",
                    "subcat/README.md": "# A Subcategory\nSome notes.",
                    "subcat/recipe.md": "# A nested recipe for 3",
                }
            )
        )

        assert h.get_breadcrumbs() == [
            ("A recipe website", "index.html"),
        ]

        assert h.scaled_categories[4].get_breadcrumbs() == [
            ("A recipe website", "../index.html"),
            ("Recipes for 4", "index.html"),
        ]

        assert h.scaled_categories[4].subcategories[0].get_breadcrumbs() == [
            ("A recipe website", "../../index.html"),
            ("Recipes for 4", "../index.html"),
            ("A Subcategory", "index.html"),
        ]

        assert h.scaled_categories[4].subcategories[0].recipes[0].get_breadcrumbs() == [
            ("A recipe website", "../../index.html"),
            ("Recipes for 4", "../index.html"),
            ("A Subcategory", "index.html"),
            ("A nested recipe", "recipe.html"),
        ]

        assert h.unscaled_categories.get_breadcrumbs() == [
            ("A recipe website", "../index.html"),
            ("Categories", "index.html"),
        ]

        assert h.unscaled_categories.subcategories[0].get_breadcrumbs() == [
            ("A recipe website", "../../index.html"),
            ("Categories", "../index.html"),
            ("A Subcategory", "index.html"),
        ]

        assert h.unscaled_categories.subcategories[0].recipes[0].get_breadcrumbs() == [
            ("A recipe website", "../../index.html"),
            ("Recipes for 3", "../index.html"),  # NB Uses native scaling
            ("A Subcategory", "index.html"),
            ("A nested recipe", "recipe.html"),
        ]

    def test_home_page(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(make_directory({}))

        assert h.home_page is h
        assert h.unscaled_categories.home_page is h

    def test_template_variables(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory(
                {"README.md": "# A recipe website", "recipe.md": "# A recipe for 3"}
            )
        )

        template_variables = h.scaled_categories[1].recipes[0].get_template_variables()

        assert template_variables["title"] == "A recipe"
        assert template_variables["site_name"] == "A recipe website"
        assert template_variables["breadcrumbs"] == [
            ("A recipe website", "../index.html"),
            ("Recipes for 1", "index.html"),
            ("A recipe", "recipe.html"),
        ]
        assert template_variables["css_href"] == "../css/style.css"


class TestHomePage:
    def test_no_index(self, make_directory: MakeDirectoryFn) -> None:
        d = make_directory({})
        h = HomePage.from_root_directory(d)
        assert h.title == "Input"
        assert h.welcome_message_html is None
        assert h.welcome_message_source is None
        assert list(h.sources()) == []

    def test_has_index(self, input_path: Path, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(make_directory({"index.md": "# Hello\nWorld"}))
        assert h.title == "Hello"
        assert h.welcome_message_html == "<p>World</p>\n"
        assert h.welcome_message_source == input_path / "index.md"

    def test_path(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(make_directory({}))
        assert h.path == "/index.html"

    def test_parent(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(make_directory({}))
        assert h.parent is None

    def test_max_servings(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(make_directory({}), max_servings=5,)
        assert set(h.scaled_categories) == set(range(1, 5 + 1))

    def test_sources_with_readme(
        self, input_path: Path, make_directory: MakeDirectoryFn
    ) -> None:
        h = HomePage.from_root_directory(make_directory({"README.md": "# A website"}))
        assert set(h.sources()) == {input_path / "README.md"}

    def test_sources_without_readme(
        self, input_path: Path, make_directory: MakeDirectoryFn
    ) -> None:
        h = HomePage.from_root_directory(make_directory({}))
        assert set(h.sources()) == set()

    def test_make_source_to_page_paths_lookup(
        self, input_path: Path, make_directory: MakeDirectoryFn
    ) -> None:
        h = HomePage.from_root_directory(
            make_directory(
                {
                    "README.md": "# A website",
                    "foo/README.md": "# Foo category",
                    "foo/recipe.md": "# A recipe for 2",
                }
            )
        )
        assert h.make_source_to_page_paths_lookup() == {
            input_path / "README.md": "/index.html",
            input_path: "/categories/index.html",
            input_path / "foo": "/categories/foo/index.html",
            input_path / "foo" / "README.md": "/categories/foo/index.html",
            input_path / "foo" / "recipe.md": "/serves2/foo/recipe.html",
        }


class TestCategoryPage:
    def test_servings(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(make_directory({}))

        assert h.scaled_categories[1].servings == 1
        assert h.scaled_categories[2].servings == 2
        assert h.unscaled_categories.servings is None

    def test_root_title(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory({"index.md": "# Hello\nWhat's up?"})
        )

        assert h.scaled_categories[1].title == "Recipes for 1"
        assert h.scaled_categories[3].title == "Recipes for 3"
        assert h.unscaled_categories.title == "Categories"

    def test_title(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory({"subcat/recipe.md": "# Recipe for 2"})
        )

        assert h.scaled_categories[1].subcategories[0].title == "Subcat"
        assert h.unscaled_categories.subcategories[0].title == "Subcat"

    def test_root_has_no_description(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory({"index.md": "# Hello\nWhat's up?"})
        )

        assert h.scaled_categories[1].description_html is None
        assert h.scaled_categories[3].description_html is None
        assert h.unscaled_categories.description_html is None

        assert h.scaled_categories[1].description_source is None
        assert h.scaled_categories[3].description_source is None
        assert h.unscaled_categories.description_source is None

    def test_description_no_readme(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory({"subcat/recipe.md": "# Recipe for 2"})
        )

        assert h.scaled_categories[1].subcategories[0].description_html is None
        assert h.scaled_categories[1].subcategories[0].description_source is None

        assert h.unscaled_categories.subcategories[0].description_html is None
        assert h.unscaled_categories.subcategories[0].description_source is None

    def test_description(
        self, input_path: Path, make_directory: MakeDirectoryFn
    ) -> None:
        h = HomePage.from_root_directory(
            make_directory(
                {
                    "subcat/README.md": "# A Subcategory\nSome notes.",
                    "subcat/recipe.md": "# Recipe for 2",
                }
            )
        )

        assert h.scaled_categories[1].subcategories[0].description_html == (
            "<p>Some notes.</p>\n"
        )
        assert h.scaled_categories[1].subcategories[0].description_source == (
            input_path / "subcat" / "README.md"
        )

        assert h.unscaled_categories.subcategories[0].description_html == (
            "<p>Some notes.</p>\n"
        )
        assert h.unscaled_categories.subcategories[0].description_source == (
            input_path / "subcat" / "README.md"
        )

    def test_root_path(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(make_directory({}))

        assert h.scaled_categories[1].path == "/serves1/index.html"
        assert h.scaled_categories[3].path == "/serves3/index.html"
        assert h.unscaled_categories.path == "/categories/index.html"

    def test_path(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory(
                {
                    "subcat/README.md": "# A Subcategory\nSome notes.",
                    "subcat/recipe.md": "# Recipe for 2",
                }
            )
        )

        assert (
            h.scaled_categories[1].subcategories[0].path == "/serves1/subcat/index.html"
        )
        assert (
            h.scaled_categories[3].subcategories[0].path == "/serves3/subcat/index.html"
        )
        assert (
            h.unscaled_categories.subcategories[0].path
            == "/categories/subcat/index.html"
        )

    def test_parent(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory({"subcat/recipe.md": "# Recipe for 2"})
        )

        assert h.scaled_categories[1].parent is h
        assert h.unscaled_categories.parent is h

        assert h.scaled_categories[1].subcategories[0].parent is h.scaled_categories[1]
        assert h.unscaled_categories.subcategories[0].parent is h.unscaled_categories

    def test_source_directory(
        self, input_path: Path, make_directory: MakeDirectoryFn
    ) -> None:
        h = HomePage.from_root_directory(
            make_directory({"subcat/recipe.md": "# Recipe for 2"})
        )

        assert h.scaled_categories[1].source_directory == input_path
        assert (
            h.scaled_categories[1].subcategories[0].source_directory
            == input_path / "subcat"
        )

        assert h.unscaled_categories.source_directory == input_path
        assert (
            h.unscaled_categories.subcategories[0].source_directory
            == input_path / "subcat"
        )

    def test_subdirectories(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory(
                {
                    "a/README.md": "# Category Z",
                    "b/README.md": "# Category Y",
                    "c/README.md": "# Category X",
                    "d/README.md": "# Category W",
                    "a/recipe.md": "# Recipe for 2",
                    "b/recipe.md": "# Recipe for 2",
                    "c/recipe.md": "# Recipe for 2",
                    "d/recipe.md": "# Recipe for 2",
                }
            )
        )

        # Subcategories should be given in title order
        assert h.scaled_categories[1].subcategories[0].title == "Category W"
        assert h.scaled_categories[1].subcategories[1].title == "Category X"
        assert h.scaled_categories[1].subcategories[2].title == "Category Y"
        assert h.scaled_categories[1].subcategories[3].title == "Category Z"

    def test_recipes(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory(
                {
                    "recipe_a.md": "# Recipe Z for 6",
                    "recipe_b.md": "# Recipe Y for 5",
                    "recipe_c.md": "# Recipe X for 4",
                    "recipe_d.md": "# Recipe W for 3",
                }
            )
        )

        # Recipes should be given in title order
        assert h.scaled_categories[1].recipes[0].title == "Recipe W"
        assert h.scaled_categories[1].recipes[1].title == "Recipe X"
        assert h.scaled_categories[1].recipes[2].title == "Recipe Y"
        assert h.scaled_categories[1].recipes[3].title == "Recipe Z"

        assert h.unscaled_categories.recipes[0].title == "Recipe W"
        assert h.unscaled_categories.recipes[1].title == "Recipe X"
        assert h.unscaled_categories.recipes[2].title == "Recipe Y"
        assert h.unscaled_categories.recipes[3].title == "Recipe Z"

        # Scaled categories should link to matching scaled recipes
        assert h.scaled_categories[1].recipes[0].servings == 1
        assert h.scaled_categories[1].recipes[1].servings == 1
        assert h.scaled_categories[1].recipes[2].servings == 1
        assert h.scaled_categories[1].recipes[3].servings == 1

        assert h.scaled_categories[3].recipes[0].servings == 3
        assert h.scaled_categories[3].recipes[1].servings == 3
        assert h.scaled_categories[3].recipes[2].servings == 3
        assert h.scaled_categories[3].recipes[3].servings == 3

        # Unscaled categories should link to natively scaled recipes
        assert h.unscaled_categories.recipes[0].servings == 3
        assert h.unscaled_categories.recipes[1].servings == 4
        assert h.unscaled_categories.recipes[2].servings == 5
        assert h.unscaled_categories.recipes[3].servings == 6

    def test_sources(self, input_path: Path, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory(
                {
                    "README.md": "# A website",
                    "bar/README.md": "# Bar category",
                    "foo/recipe.md": "# A recipe for 2",
                }
            )
        )

        # Root category never credited with the README
        assert set(h.unscaled_categories.sources()) == {input_path}

        # Unscaled page with README is credited with the source
        assert set(h.unscaled_categories.subcategories[0].sources()) == {
            input_path / "bar" / "README.md",
            input_path / "bar",
        }

        # Unscaled page with no README also a source but just has directory
        assert set(h.unscaled_categories.subcategories[1].sources()) == {
            input_path / "foo",
        }

        # Scaled page has nothing
        assert set(h.scaled_categories[1].sources()) == set()
        assert set(h.scaled_categories[1].subcategories[0].sources()) == set()
        assert set(h.scaled_categories[1].subcategories[1].sources()) == set()


class TestRecipePage:
    def test_title(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory({"recipe.md": "# A recipe for 3"})
        )
        assert h.scaled_categories[1].recipes[0].title == "A recipe"
        assert h.unscaled_categories.recipes[0].title == "A recipe"

    def test_path(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory(
                {
                    "recipe.md": "# A recipe for 3",
                    "subcat/foobar.md": "# A recipe for 3",
                }
            )
        )

        assert h.scaled_categories[1].recipes[0].path == "/serves1/recipe.html"
        assert h.unscaled_categories.recipes[0].path == "/serves3/recipe.html"

        assert h.scaled_categories[1].subcategories[0].recipes[0].path == (
            "/serves1/subcat/foobar.html"
        )
        assert h.unscaled_categories.subcategories[0].recipes[0].path == (
            "/serves3/subcat/foobar.html"
        )

    def test_parent(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory({"recipe.md": "# A recipe for 3"})
        )

        assert h.scaled_categories[1].recipes[0].parent is h.scaled_categories[1]
        assert h.unscaled_categories.recipes[0].parent is h.scaled_categories[3]

    def test_servings(self, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory({"recipe.md": "# A recipe for 3"})
        )

        assert h.scaled_categories[1].recipes[0].servings == 1
        assert h.scaled_categories[4].recipes[0].servings == 4
        assert h.unscaled_categories.recipes[0].servings == 3

        assert h.scaled_categories[1].recipes[0].native_servings == 3
        assert h.scaled_categories[4].recipes[0].native_servings == 3
        assert h.unscaled_categories.recipes[0].native_servings == 3

    def test_recipe_source(
        self, input_path: Path, make_directory: MakeDirectoryFn
    ) -> None:
        h = HomePage.from_root_directory(
            make_directory({"recipe.md": "# A recipe for 3"})
        )

        assert (
            h.scaled_categories[1].recipes[0].recipe_source == input_path / "recipe.md"
        )
        assert (
            h.unscaled_categories.recipes[0].recipe_source == input_path / "recipe.md"
        )

    def test_max_servings_too_low(self, make_directory: MakeDirectoryFn) -> None:
        with pytest.raises(MaxServingsLowerThanLargestRecipeError):
            HomePage.from_root_directory(
                make_directory({"recipe.md": "# Food for 5000"}), max_servings=5,
            )

    def test_resolve_local_links_stage(
        self, input_path: Path, make_directory: MakeDirectoryFn
    ) -> None:
        h = HomePage.from_root_directory(
            make_directory({"foo/recipe.md": "# Recipe for 2", "foo/file.txt": "..."}),
        )

        filename_to_asset_paths: MutableMapping[Path, str] = {}
        stage = (
            h.scaled_categories[3]
            .subcategories[0]
            .recipes[0]
            .get_resolve_local_links_stage(
                source=input_path / "foo" / "recipe.md",
                source_to_page_paths={
                    input_path / "README.md": "/categories/index.html",
                    input_path / "foo" / "recipe.md": "/serves2/foo/recipe.html",
                },
                filename_to_asset_paths=filename_to_asset_paths,
            )
        )

        for href, exp_href in [
            # Check directory is correct
            ("recipe.md", "recipe.html"),
            # Check path is right (i.e. uses same number of servings
            ("../README.md", "../index.html"),
            # Check asset paths updated and asset dir is correct
            ("file.txt", "../../assets/foo/file.txt"),
        ]:
            assert postprocess_html(t("a", "foo", href=href), False, [stage]) == t(
                "a", "foo", href=exp_href
            )

        assert filename_to_asset_paths == {
            input_path / "foo" / "file.txt": "/assets/foo/file.txt",
        }

        # Check root is correctly set
        with pytest.raises(LinkToExternalFileError):
            postprocess_html(t("a", "foo", href="../../../foo.bar"), False, [stage])

    def test_sources(self, input_path: Path, make_directory: MakeDirectoryFn) -> None:
        h = HomePage.from_root_directory(
            make_directory({"recipe.md": "# A recipe for 2"})
        )

        # Native scaling has source
        assert set(h.scaled_categories[2].recipes[0].sources()) == {
            input_path / "recipe.md"
        }

        # Non-native scaling does not
        assert set(h.scaled_categories[1].recipes[0].sources()) == set()


class TestGenerateStaticSite:
    @pytest.fixture
    def sample_site_path(self, make_directory: MakeDirectoryFn) -> Path:
        return make_directory(
            {
                # Index page contains links
                "index.md": (
                    "# A static website\n"
                    "With some ace recipes, [like this one](recipe.md)"
                ),
                # Recipe page contains links
                "recipe.md": (
                    "# A recipe for 3\n"
                    "Pretty nice. See also the [foo category](foo) of recipes."
                ),
                # Category page contains links in other directories
                "foo/index.md": (
                    "# Foo recipes\n"
                    "These are even better than [previous recipes](..) like "
                    "[this one](../recipe.md), how about this "
                    "[delicious foo recipe](100%_foo_'recipe'.md)?"
                ),
                # Recipe page:
                # * Its filename contains a symbols which requires escaping in URLs
                #   and HTML attributes alike
                # * Contains a reference to a static file
                # * Contains internal recipe anchor links
                "foo/100%_foo_'recipe'.md": (
                    "# A foo recipe for 7\n"
                    "It's delicious!\n"
                    "```recipe\n"
                    "pizza = order(takeaway pizza)\n"
                    "```\n"
                    "Yep then to serve, just:\n"
                    "```recipe\n"
                    "pizza, slice, distribute\n"
                    "```\n"
                    "When you're done eating that, take a look at [this file](file.txt)!"
                ),
                # A static file
                "foo/file.txt": "Hey there...",
            }
        )

    def test_no_dead_links(self, sample_site_path: Path, output_path: Path) -> None:
        generate_static_site(sample_site_path, output_path)

        for page_path in output_path.glob("**/*.html"):
            page_html = page_path.open().read()
            page_root = lxml.html.document_fromstring(page_html)

            for element, attribute, link, pos in page_root.iterlinks():
                parts = urlsplit(link)
                if parts.scheme != "" or parts.netloc != "" or parts.path == "":
                    continue

                link_path = page_path.parent / Path(*unquote(parts.path).split("/"))

                # Referenced file should exist
                assert link_path.is_file()

                # Referenced file should be in output directory
                assert (
                    link_path.resolve().parts[: len(output_path.parts)]
                    == output_path.parts
                )
