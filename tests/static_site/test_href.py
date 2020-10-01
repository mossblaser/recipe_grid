import pytest

from recipe_grid.static_site import href


@pytest.mark.parametrize(
    "url, exp",
    [
        ("/index.html", ""),
        ("/foo/index.html", "/foo"),
        ("/foo/bar/baz.html", "/foo/bar"),
    ],
)
def test_parent(url: str, exp: str) -> None:
    assert href.parent(url) == exp


@pytest.mark.parametrize(
    "a, b, exp",
    [
        # Self
        ("/index.html", "/index.html", "index.html"),
        ("/foo/index.html", "/foo/index.html", "index.html"),
        # Same directory
        ("/index.html", "/bar.html", "bar.html"),
        ("/foo/index.html", "/foo/bar.html", "bar.html"),
        # Child directory
        ("/index.html", "/bar/baz.html", "bar/baz.html"),
        ("/foo/index.html", "/foo/bar/baz.html", "bar/baz.html"),
        # Parent directory
        ("/foo/index.html", "/baz.html", "../baz.html"),
        ("/foo/bar/index.html", "/foo/baz.html", "../baz.html"),
        # Multiple levels of parent up
        ("/foo/bar/index.html", "/baz.html", "../../baz.html"),
        # Shared ancestor only
        ("/foo/bar/baz.html", "/foo/qux/quo.html", "../qux/quo.html"),
        ("/foo/bar/index.html", "/qux/bar/quo.html", "../../qux/bar/quo.html"),
    ],
)
def test_relative(a: str, b: str, exp: str) -> None:
    assert href.relative(a, b) == exp
