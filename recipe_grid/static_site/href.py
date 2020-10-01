"""
Utilities for working with HREFs.
"""

from typing import List


def parent(href: str) -> str:
    """
    Get the parent directory of the specified file or directory.

    Example::

        >>> parent("/foo/bar.html")
        "/foo"
    """
    return "/".join(href.split("/")[:-1])


def relative(from_href: str, to_href: str) -> str:
    """
    Create a relative path which links from ``from_href`` to ``to_href``.

    Example::

        >>> relative("/foo/bar/baz.html", "/foo/qux/quo.html")
        "../qux/quo.html"
    """
    from_parts = from_href.split("/")[:-1]  # NB: Ignore current filename
    to_parts = to_href.split("/")

    common_parts: List[str] = []
    for a, b in zip(from_parts, to_parts):
        if a != b:
            break
        common_parts.append(a)

    up_to_common = [".."] * (len(from_parts) - len(common_parts))
    down_to_new = to_parts[len(common_parts) :]

    return "/".join(up_to_common + down_to_new)
