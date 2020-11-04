"""
Routines for post-processing HTML, e.g. rewriting links etc.
"""

from typing import List, Tuple, Optional, Callable, Mapping, MutableMapping

from pathlib import Path

from urllib.parse import urlsplit, urlunsplit, quote, unquote

from copy import deepcopy

import mimetypes

from base64 import b64encode

import lxml.html  # type: ignore

from recipe_grid.static_site.exceptions import (
    LinkToExternalFileError,
    LinkToNonExistentFileError,
)

from recipe_grid.static_site import href


HTMLPostprocessingStage = Callable[[lxml.html.Element], Optional[lxml.html.Element]]
"""
Function which post-processes a lxml.html.Element tree, optionally returning
the modified element (or modifying in place if None is returned).
"""


def postprocess_html(
    html: str,
    complete_document: bool = True,
    stages: List[HTMLPostprocessingStage] = [],
) -> str:
    """
    Post-process a HTML document of fragment with the specified processing
    stages which manipulate the document.

    Parameters
    ==========
    html : str
        The HTML source.
    complete_document : str
        If ``html`` is a complete HTML document, this must be True, otherwise
        for HTML fragments, this must be false.
    stages : [ElementTree -> ElementTree or None, ...]
        A series of post-processing stages which transform the lxml parsed
        representation of the provided HTML. If the function returns None, the
        previous provided element tree will be assumed to be modified in-place.

        Note that when complete_document is False, the provided HTML will be
        logically wrapped in a <div> tag. This tag must not be modified or
        removed. The tag will be dropped again in the final output.
    """
    if complete_document:
        tree = lxml.html.document_fromstring(html)
    else:
        # NB: Wrap in <div> because lxml cannot handle things like bare text or
        # sequences of tags as a fragment.
        tree = lxml.html.fragment_fromstring(f"<div>{html}</div>")

    for stage in stages:
        new_tree = stage(tree)
        if new_tree is not None:
            tree = new_tree

    html = lxml.html.tostring(tree).decode("utf-8")

    # Remove <div> wrapper if fragment was used
    if not complete_document:
        empty, open_div, html = html.partition("<div>")
        assert open_div == "<div>"
        assert empty == ""
        html, close_div, empty = html.rpartition("</div>")
        assert close_div == "</div>"
        assert empty == ""

    return html


def resolve_local_links(
    tree: lxml.etree.Element,
    source: Path,
    root: Path,
    from_path: str,
    source_to_page_paths: Mapping[Path, Tuple[str, bool]],
    filename_to_asset_paths: MutableMapping[Path, str],
    assets_dir_path: str,
) -> None:
    """
    A post-processing stage which resolves local URLs (e.g. to other recipes or
    image files).

    Parameters
    ==========
    tree: lxml.etree.ElementTree
        The tree in which rewrite_links will be called.
    source: Path
        The filename of the source file where the links were originally
        defined.
    root: Path
        The root directory containing the source. References will not be
        allowed to files outside this directory tree.
    from_path: str
        The website page path to the page being transformed. Used to construct
        relative hrefs.
    source_to_page_paths: {source_filename: (site_path, is_scalable), ...}
        A lookup from (resolved) paths to website page paths corresponding
        to that source. The is_scalable boolean indicates if the page is
        scalable (e.g. recipes which can be scaled, or a category page) or not
        (e.g. unscalable recipes). In the former case, the first part of the
        site path may be modified to contain a different serving count.

        Used to substitute links to markdown files with their
        compiled recipe pages and links to directories or READMEs with the
        corresponding website page.

        The paths to recipes should point to the page containing the native
        serving size for that recipe.

        Paths to directories should point to the unscaled version of the
        corresponding page (i.e. "/categories/..." path).

        When substitutions are being made, if we're on a recipe or category
        page scaled to a particular number, links to other recipes will use the
        version of the page with the matching scale. Otherwise, the native
        scaling or unscaled page will be referenced.
    filename_to_asset_paths : {filename: site_path, ...}
        A dictionary mapping from (resolved) filenames to website paths to use
        for that static content. This dictionary will be populated
        automatically with all referenced local files, relocated to a website
        path of "<assets_dir_path>/<original file path relative to root>".
    assets_dir_path : site_path
        The path of the assets directory (*without* a trailing slash) where all
        assets will be copied to.
    """

    def rewrite_link(url: str) -> str:
        parts = urlsplit(url)

        # Don't rewrite external links, or links within the page
        if parts.scheme != "" or parts.netloc != "" or parts.path == "":
            return url

        path = unquote(parts.path)

        # Work out the local file system path the URL points at
        fspath: Path
        if path.startswith("/"):
            fspath = root / Path(*path.split("/")[1:])
        else:
            fspath = source.parent / Path(*path.split("/"))
        fspath = fspath.resolve()

        # Work out where on the website this points
        website_path: str
        if fspath in source_to_page_paths:
            website_path, is_scalable = source_to_page_paths[fspath]

            # Change serving number to match current page, if it's path starts
            # with "/serves", except for unscaled recipes
            if from_path.startswith("/serves") and is_scalable:
                website_path = "/".join(
                    from_path.split("/")[:2] + website_path.split("/")[2:]
                )
        else:
            # Verify that the local file exists and is not outside the source
            # root
            root_parts = root.resolve().parts
            if fspath.parts[: len(root_parts)] != root_parts:
                raise LinkToExternalFileError(
                    f"{source} contains a link to a file outside the website source: {url}"
                )
            if not fspath.is_file():
                raise LinkToNonExistentFileError(
                    f"{source} contains a link to non-existent file: {url}"
                )

            # Add the referenced external file to the assets dict
            website_path = (
                assets_dir_path + "/" + "/".join(fspath.parts[len(root_parts) :])
            )
            filename_to_asset_paths[fspath] = website_path

        # Create a relative link
        relative_path = href.relative(from_path, website_path)

        # Reconstitute the URL
        return urlunsplit(parts._replace(path=quote(relative_path)))

    tree.rewrite_links(rewrite_link)


def add_recipe_scaling_links(
    tree: lxml.etree.Element,
    from_path: str,
    scaled_paths: Mapping[int, str],
    native_servings: int,
) -> None:
    """
    A post-processing stage which adds links to other scalings of a recipe to a
    recipe page.

    Parameters
    ==========
    tree: lxml.etree.ElementTree
        The tree in which rewrite_links will be called.
    from_path: str
        The website page path to the page being transformed. Used to construct
        relative hrefs.
    scaled_paths: {servings: site_path, ...}
        A lookup from serving count to paths to scaled pages.
    native_servings : int
        The native number of servings for this recipe.
    """
    for span in tree.find_class("rg-serving-count"):
        # Generate links with each of the different scalings
        scaling_links = []
        for servings, scaled_path in sorted(scaled_paths.items()):
            span_copy = deepcopy(span)
            number = span_copy.find_class("rg-scaled-value")[0]
            number.text = str(servings)
            link = lxml.html.Element("a", href=href.relative(from_path, scaled_path))
            link.text = span_copy.text
            link.extend(span_copy)
            scaling_links.append(link)

        # Wrap current count in link
        current = lxml.html.Element(
            "a", {"href": "#", "class": "rg-serving-count-current"}
        )
        current.extend(span)
        current.text = span.text
        span.text = ""
        span.append(current)

        # Add dropdown list of scalings (to be revealed by CSS)
        dropdown = lxml.html.Element("ul")
        for link in scaling_links:
            li = lxml.html.Element("li")
            li.append(link)
            dropdown.append(li)
        span.append(dropdown)

    for span in tree.find_class("rg-original-servings"):
        # Wrap original serving count in a link to that number of servings
        link = lxml.html.Element(
            "a", href=href.relative(from_path, scaled_paths[native_servings])
        )
        link.text = span.text
        link.extend(span)
        span.append(link)
        span.text = ""


def embed_local_links_as_data_urls(
    tree: lxml.etree.Element,
    source: Path,
    root: Path,
) -> None:
    """
    A post-processing stage which converts local URLs into data URLs containing
    the linked content.

    Parameters
    ==========
    tree: lxml.etree.ElementTree
        The tree in which rewrite_links will be called.
    source: Path
        The filename of the source file where the links were originally
        defined.
    root: Path
        The root directory containing the source. References will not be
        allowed to files outside this directory tree.
    """

    def rewrite_link(url: str) -> str:
        parts = urlsplit(url)

        # Don't rewrite external links, or links within the page
        if parts.scheme != "" or parts.netloc != "" or parts.path == "":
            return url

        path = unquote(parts.path)

        # Work out the local file system path the URL points at
        fspath: Path
        if path.startswith("/"):
            fspath = root / Path(*path.split("/")[1:])
        else:
            fspath = source.parent / Path(*path.split("/"))
        fspath = fspath.resolve()

        # Verify that the local file exists and is not outside the source
        # root
        root_parts = root.resolve().parts
        if fspath.parts[: len(root_parts)] != root_parts:
            raise LinkToExternalFileError(
                f"{source} contains a link to a file outside the website source: {url}"
            )
        if not fspath.is_file():
            raise LinkToNonExistentFileError(
                f"{source} contains a link to non-existent file: {url}"
            )

        # Guess mimetype
        mimetype, _encoding = mimetypes.guess_type(fspath)
        if mimetype is None:
            mimetype = "application/octet-stream"

        # Base64 encode
        base64_data = b64encode(fspath.open("rb").read()).decode("ascii")

        return f"data:{mimetype};base64,{base64_data}"

    tree.rewrite_links(rewrite_link)
