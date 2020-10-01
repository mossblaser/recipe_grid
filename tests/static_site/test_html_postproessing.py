import pytest

from typing import Mapping, MutableMapping

from pathlib import Path

from functools import partial

from fractions import Fraction

from recipe_grid.renderer.html import t

from recipe_grid.markdown import compile_markdown

from recipe_grid.static_site.exceptions import (
    LinkToExternalFileError,
    LinkToNonExistentFileError,
)

from recipe_grid.static_site.html_postprocessing import (
    postprocess_html,
    resolve_local_links,
    add_recipe_scaling_links,
    embed_local_links_as_data_urls,
)


class TestPostprocessHTML:
    @pytest.mark.parametrize(
        "source, exp",
        [
            # Bare-bones
            ("<html></html>", "<html></html>"),
            # Some content
            (
                "<html><body><h1>Hello!</h1></body></html>",
                "<html><body><h1>Hello!</h1></body></html>",
            ),
            # With whitespace
            (
                "<html><body>\n  <h1>Hello!</h1>\n</body></html>",
                "<html><body>\n  <h1>Hello!</h1>\n</body></html>",
            ),
        ],
    )
    def test_document_passthrough(self, source: str, exp: str) -> None:
        assert postprocess_html(source) == exp

    @pytest.mark.parametrize(
        "source, exp",
        [
            # Empty
            ("", ""),
            # Just text
            ("foo bar", "foo bar"),
            # Whitespace preserved
            ("foo \n bar", "foo \n bar"),
            # Text'n'tags
            ("Foo <b>bar</b> baz", "Foo <b>bar</b> baz"),
            # Tags
            ("<h1>bar</h1>", "<h1>bar</h1>"),
        ],
    )
    def test_fragment_passthrough(self, source: str, exp: str) -> None:
        assert postprocess_html(source, False) == exp

    def test_processing(self) -> None:
        # NB: Order of processing steps is checked
        assert (
            postprocess_html(
                '<a href="foo/bar">Foo-bar</a>',
                False,
                [
                    # Capitalise first letter
                    lambda t: t.rewrite_links(lambda url: url[0].upper() + url[1:]),
                    # Swap around "/"
                    lambda t: t.rewrite_links(
                        lambda url: "/".join(url.split("/")[::-1])
                    ),
                    # Return a tree
                    lambda t: t,
                ],
            )
            == '<a href="bar/Foo">Foo-bar</a>'
        )


class TestResolveLocalLinks:
    def run(
        self,
        html: str,
        tmp_path: Path,
        source: Path,
        from_path: str,
        filename_to_asset_paths: MutableMapping[str, str],
    ) -> str:
        d = tmp_path / "foo" / "bar"
        d.mkdir(parents=True, exist_ok=True)
        (d / "file.txt").open("w").write("Hello!")
        return postprocess_html(
            html,
            False,
            [
                partial(
                    resolve_local_links,
                    source=source,
                    root=tmp_path / "foo",
                    from_path=from_path,
                    source_to_page_paths={
                        tmp_path / "foo" / "bar" / "baz.md": "/serves2/bar/baz.html",
                        tmp_path / "foo" / "bar" / "same.md": "/serves3/bar/same.html",
                        tmp_path / "foo" / "parent.md": "/serves5/parent.html",
                        # Index pages
                        tmp_path / "foo" / "README.md": "/categories/index.html",
                        tmp_path
                        / "foo"
                        / "bar"
                        / "README.md": "/categories/bar/index.html",
                        # Directories
                        tmp_path / "foo": "/categories/index.html",
                        tmp_path / "foo" / "bar": "/categories/bar/index.html",
                    },
                    filename_to_asset_paths=filename_to_asset_paths,
                    assets_dir_path="/static",
                )
            ],
        )

    @pytest.mark.parametrize(
        "link, exp_link, exp_filename_to_asset_paths",
        [
            # Implied current page link
            ("", "", {}),
            ("#foo", "#foo", {}),
            # Link to category page
            ("/bar", "index.html", {}),
            ("/bar/", "index.html", {}),
            ("/bar/README.md", "index.html", {}),
            ("/", "../index.html", {}),
            ("/README.md", "../index.html", {}),
            # Link to file
            (
                "file.txt",
                "../../static/bar/file.txt",
                {Path("foo", "bar", "file.txt"): "/static/bar/file.txt"},
            ),
        ],
    )
    @pytest.mark.parametrize(
        "source, from_path",
        [
            # Recipe
            (Path("foo", "bar", "baz.md"), "/serves123/bar/baz.html"),
            # Scaled category
            (Path("foo", "bar", "index.md"), "/serves123/bar/index.html"),
            # Unscaled category
            (Path("foo", "bar", "index.md"), "/categories/bar/index.html"),
        ],
    )
    def test_any_page_cases(
        self,
        tmp_path: Path,
        link: str,
        exp_link: str,
        exp_filename_to_asset_paths: Mapping[str, str],
        source: Path,
        from_path: str,
    ) -> None:
        filename_to_asset_paths: MutableMapping[str, str] = {}
        assert self.run(
            t("a", "Link", href=link),
            tmp_path=tmp_path,
            source=tmp_path / source,
            from_path=from_path,
            filename_to_asset_paths=filename_to_asset_paths,
        ) == t("a", "Link", href=exp_link)
        assert filename_to_asset_paths == {
            tmp_path / file: path for file, path in exp_filename_to_asset_paths.items()
        }

    @pytest.mark.parametrize(
        "link, exp_link",
        [
            # Relative link to current page (should keep the scale)
            ("baz.md", "baz.html"),
            ("./baz.md", "baz.html"),
            ("../bar/baz.md", "baz.html"),
            ("../bar/baz.md#foo", "baz.html#foo"),
        ],
    )
    def test_from_recipe_page(self, tmp_path: Path, link: str, exp_link: str,) -> None:
        filename_to_asset_paths: MutableMapping[str, str] = {}
        assert self.run(
            t("a", "Link", href=link),
            tmp_path=tmp_path,
            source=tmp_path / "foo" / "bar" / "baz.md",
            from_path="/serves123/bar/baz.html",
            filename_to_asset_paths=filename_to_asset_paths,
        ) == t("a", "Link", href=exp_link)
        assert filename_to_asset_paths == {}

    @pytest.mark.parametrize(
        "link, exp_link",
        [
            # Relative link to current page (should keep scale)
            ("README.md", "index.html"),
            ("./README.md", "index.html"),
            ("../bar/README.md", "index.html"),
            ("../bar/README.md#foo", "index.html#foo"),
            # Absolute link to current page (should keep scale)
            ("/bar/README.md", "index.html"),
            # Link to recipe page (should keep scale)
            ("same.md", "same.html"),
            ("/bar/same.md", "same.html"),
            ("../parent.md", "../parent.html"),
            ("/parent.md", "../parent.html"),
        ],
    )
    def test_from_scaled_category_page(
        self, tmp_path: Path, link: str, exp_link: str,
    ) -> None:
        filename_to_asset_paths: MutableMapping[str, str] = {}
        assert self.run(
            t("a", "Link", href=link),
            tmp_path=tmp_path,
            source=tmp_path / "foo" / "bar" / "README.md",
            from_path="/serves123/bar/index.html",
            filename_to_asset_paths=filename_to_asset_paths,
        ) == t("a", "Link", href=exp_link)
        assert filename_to_asset_paths == {}

    @pytest.mark.parametrize(
        "link, exp_link",
        [
            # Relative link to current page (should remain unscaled)
            ("README.md", "index.html"),
            ("./README.md", "index.html"),
            ("../bar/README.md", "index.html"),
            ("../bar/README.md#foo", "index.html#foo"),
            # Absolute link to current page (should remain unscaled)
            ("/bar/README.md", "index.html"),
            # Link to recipe page (should use native scale)
            ("same.md", "../../serves3/bar/same.html"),
            ("/bar/same.md", "../../serves3/bar/same.html"),
            ("../parent.md", "../../serves5/parent.html"),
            ("/parent.md", "../../serves5/parent.html"),
        ],
    )
    def test_from_unscaled_category_page(
        self, tmp_path: Path, link: str, exp_link: str,
    ) -> None:
        filename_to_asset_paths: MutableMapping[str, str] = {}
        assert self.run(
            t("a", "Link", href=link),
            tmp_path=tmp_path,
            source=tmp_path / "foo" / "bar" / "README.md",
            from_path="/categories/bar/index.html",
            filename_to_asset_paths=filename_to_asset_paths,
        ) == t("a", "Link", href=exp_link)
        assert filename_to_asset_paths == {}


def test_add_recipe_scaling_links() -> None:
    html = compile_markdown("# A recipe serving 3").render(Fraction(2, 3))

    assert postprocess_html(
        html,
        False,
        [
            partial(
                add_recipe_scaling_links,
                from_path="/serves2/foo/bar.html",
                scaled_paths={
                    1: "/serves1/foo/bar.html",
                    2: "/serves2/foo/bar.html",
                    3: "/serves3/foo/bar.html",
                    4: "/serves4/foo/bar.html",
                },
                native_servings=3,
            )
        ],
    ) == (
        '<header><h1 class="rg-title-scalable">A recipe '
        '<span class="rg-serving-count">'
        '<a href="#" class="rg-serving-count-current">'
        'serving <span class="rg-scaled-value">2</span>'
        "</a>"
        "<ul>"
        '<li><a href="../../serves1/foo/bar.html">serving '
        '<span class="rg-scaled-value">1</span></a></li>'
        '<li><a href="bar.html">serving '
        '<span class="rg-scaled-value">2</span></a></li>'
        '<li><a href="../../serves3/foo/bar.html">serving '
        '<span class="rg-scaled-value">3</span></a></li>'
        '<li><a href="../../serves4/foo/bar.html">serving '
        '<span class="rg-scaled-value">4</span></a></li>'
        "</ul>"
        "</span></h1><p>Rescaled from "
        '<span class="rg-original-servings">'
        '<a href="../../serves3/foo/bar.html">3 servings</a></span>.</p>'
        "</header>\n"
    )


class TestEmbedLocalLinksAsDataUrls:
    @pytest.mark.parametrize(
        "url", ["http://example.com", "#foo"],
    )
    def test_ignore_external_or_page_local_links(
        self, tmp_path: Path, url: str
    ) -> None:
        html = t("a", "foo", href=url)

        assert (
            postprocess_html(
                html,
                False,
                [
                    partial(
                        embed_local_links_as_data_urls,
                        source=tmp_path / "foo.md",
                        root=tmp_path,
                    ),
                ],
            )
            == html
        )

    def test_path_outside_root(self, tmp_path: Path) -> None:
        with pytest.raises(LinkToExternalFileError):
            postprocess_html(
                t("a", "foo", href="../bar.txt"),
                False,
                [
                    partial(
                        embed_local_links_as_data_urls,
                        source=tmp_path / "foo.md",
                        root=tmp_path,
                    ),
                ],
            )

    def test_path_does_not_exist(self, tmp_path: Path) -> None:
        with pytest.raises(LinkToNonExistentFileError):
            postprocess_html(
                t("a", "foo", href="bar.txt"),
                False,
                [
                    partial(
                        embed_local_links_as_data_urls,
                        source=tmp_path / "foo.md",
                        root=tmp_path,
                    ),
                ],
            )

    def test_valid(self, tmp_path: Path) -> None:
        (tmp_path / "bar.txt").open("w").write("foobar")

        assert postprocess_html(
            t("a", "foo", href="bar.txt"),
            False,
            [
                partial(
                    embed_local_links_as_data_urls,
                    source=tmp_path / "foo.md",
                    root=tmp_path,
                ),
            ],
        ) == t("a", "foo", href="data:text/plain;base64,Zm9vYmFy")
