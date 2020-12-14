"""
Static recipe website site generator, for a site with many pages.

URL Scheme
==========

The static site uses the following URL scheme where ``/`` is used to indicate
the site root:

* ``/index.html``: Homepage
* ``/serves<N>/index.html``: Root category page (scaled to <N> servings).
* ``/categories/index.html``: Root category page (scaled to native number of servings).
* ``/<...>/<category>/index.html``: Category browsing page
* ``/serves<N>/<categories>/<recipe>.html``: Recipe webpages, for scalable
  recipes only (i.e. ones with a serving count in the title).
* ``/categories/<categories>/<recipe>.html``: Recipe webpages, for unscalable
  recipes only (i.e. ones without a serving count in the title).

The following additional paths store static resources:

* ``/css/style.css``: The site stylesheet (see :py:data:`CSS_PATH`)
* ``/assets/<...>``: Other assets (e.g. images) reference by the recipes (see
  :py:data:`ASSETS_DIR_PATH`).

"""

from typing import (
    Union,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Tuple,
    Iterator,
    Any,
    cast,
)

from pathlib import Path

from functools import partial

from fractions import Fraction

from dataclasses import dataclass, field

from shutil import copyfile

from recipe_grid.static_site.exceptions import MaxServingsLowerThanLargestRecipeError

from recipe_grid.static_site.recipe_directory import (
    enumerate_recipe_directory,
    compile_recipe_markdown,
)

from recipe_grid.static_site import href

from recipe_grid.static_site.html_postprocessing import (
    HTMLPostprocessingStage,
    postprocess_html,
    resolve_local_links,
    add_recipe_scaling_links,
)

from recipe_grid.static_site.templates import (
    homepage_template,
    categories_template,
    recipe_template,
    website_css_template,
)


CSS_PATH = "/css/style.css"
"""
The absolute website path to the site's CSS file.
"""

ASSETS_DIR_PATH = "/assets"
"""
The absolute website path to the recipe page assets directory. (Without a
trailing slash.)
"""


@dataclass
class Page:
    """Base class for all pages in the site."""

    title: str
    """The page title."""

    @property
    def path(self) -> str:
        """
        The absolute path of this page in the generated website (e.g. "/index.html"
        or "/foo/bar.html"). Starts with a leading slash (i.e. must be absolute)
        and full non-default-index-page paths must be used (i.e. write
        "/foo/index.html" not "/foo/").
        """
        raise NotImplementedError()

    parent: Optional["Page"]
    """The logical parent of this page. Used to construct breadcrumbs."""

    @property
    def home_page(self) -> "HomePage":
        """A reference to the site's homepage."""
        if self.parent is None:
            assert isinstance(self, HomePage)
            return self
        else:
            return self.parent.home_page

    def children(self) -> Iterator["Page"]:
        """
        iterate over pages which logically appear below this in the hierarchy.
        (Does not include pages referenced elsewhere in the hierarchy).
        """
        raise NotImplementedError()

    def iter_all_pages(self) -> Iterator["Page"]:
        """
        Iterate over all pages from this page downard in the logical page
        hierarchy.
        """
        yield self
        for child in self.children():
            yield from child.iter_all_pages()

    def sources(self) -> Iterator[Path]:
        """
        Iterate over the filenames (or directories, if applicable) for which
        this page is the definitive rendering. For example, the page containing
        the native scaling of a recipe would produce its source file but other
        scaling would produce nothing. Likewise, an unscaled category might
        return its README path and its directory while a scaled one would not.
        """
        raise NotImplementedError()

    def get_breadcrumbs(self, from_path: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        Get the breadcrumb bar entries for this page.

        Parameters
        ==========
        from_path : str or None
            If given, the page from which hrefs in the breadcrumb bar should be
            relative to. If None, defaults to this page
        """
        if from_path is None:
            from_path = self.path

        parent_breadcrumbs: List[Tuple[str, str]] = []
        if self.parent is not None:
            parent_breadcrumbs = self.parent.get_breadcrumbs(from_path)

        return parent_breadcrumbs + [(self.title, href.relative(from_path, self.path))]

    def get_template_variables(self) -> Mapping[str, Any]:
        """
        Get the variables to be substituted into the page template.
        """

        return {
            "title": self.title,
            "site_name": self.home_page.title,
            "breadcrumbs": self.get_breadcrumbs(),
            "css_href": href.relative(self.path, CSS_PATH),
        }

    def get_resolve_local_links_stage(
        self,
        source: Path,
        source_to_page_paths: Mapping[Path, Tuple[str, bool]],
        filename_to_asset_paths: MutableMapping[Path, str],
    ) -> HTMLPostprocessingStage:
        """
        Get a partially applied version of the :py:func:~resolve_local_links`
        :py:func:`~postprocess_html` stage with all but the source tree
        argument assigned.

        The 'source' argument should be the path to the source file used to
        generate the HTML being post-processed.

        See :py:meth:`render` for the meaning of the other arguments to this method.
        """
        return cast(
            HTMLPostprocessingStage,
            partial(
                resolve_local_links,
                source=source,
                root=self.home_page.source_root_directory,
                from_path=self.path,
                source_to_page_paths=source_to_page_paths,
                filename_to_asset_paths=filename_to_asset_paths,
                assets_dir_path=ASSETS_DIR_PATH,
            ),
        )

    def render(
        self,
        source_to_page_paths: Mapping[Path, Tuple[str, bool]],
        filename_to_asset_paths: MutableMapping[Path, str],
    ) -> str:
        """
        Render this page.

        Parameters
        ==========
        source_to_page_paths : {fs_path: (site_path, is_scalable), ...}
            A dictionary pre-populated with a mapping from website page source
            filenames to the corresponding page path on the website (and a
            boolean indicating if this page exists at other scales or not --
            i.e. that the first part of the site path can be replaced with
            different scales).

            The paths to recipes should point to the page containing the native
            serving size for that recipe.

            Paths to directories should point to the unscaled version of the
            corresponding page (i.e. ["categories", ...] path).
        filename_to_asset_paths : {fs_path: site_path, ...}
            A dictionary into which any additional assets referenced by this
            page will be logged (and therefore must be copied into the
            generated website.
        """
        raise NotImplementedError()


@dataclass
class HomePage(Page):
    """
    The root page of the website.
    """

    source_root_directory: Path
    """The root directory of the recipe website sources."""

    welcome_message_html: Optional[str]
    """HTML introductory message."""

    welcome_message_source: Optional[Path]
    """The markdown file the welcome message was read from."""

    scaled_categories: MutableMapping[int, "CategoryPage"] = field(default_factory=dict)
    """Serving-scaled category pages."""

    unscaled_categories: "CategoryPage" = cast("CategoryPage", None)
    """Unscaled category page"""

    @classmethod
    def from_root_directory(
        cls,
        root_directory: Path,
        max_servings: int = 10,
    ) -> "HomePage":
        """
        Create a complete hierarchy of pages from a root directory.

        Parameters
        ==========
        root_directory: Path
            The root directory of the recipe website sources.
        max_servings: int
            The maximum number of servings to scale recipes to. Must be at
            least as high as the largest number of servings a recipe is scaled
            for.
        """
        root = enumerate_recipe_directory(root_directory)

        homepage = cls(
            title=root.title,
            parent=None,
            source_root_directory=root_directory,
            welcome_message_html=root.description_html,
            welcome_message_source=root.description_source,
        )

        recipe_pages: MutableMapping[
            Path, MutableMapping[Optional[int], RecipePage]
        ] = {}
        homepage.scaled_categories = {
            servings: CategoryPage.from_directory(
                servings=servings,
                directory_path=root_directory,
                parent=homepage,
                recipe_pages=recipe_pages,
            )
            for servings in range(1, max_servings + 1)
        }
        homepage.unscaled_categories = CategoryPage.from_directory(
            servings=None,
            directory_path=root_directory,
            parent=homepage,
            recipe_pages=recipe_pages,
        )

        return homepage

    @property
    def path(self) -> str:
        return "/index.html"

    def children(self) -> Iterator["CategoryPage"]:
        yield from self.scaled_categories.values()
        yield self.unscaled_categories

    def sources(self) -> Iterator[Path]:
        if self.welcome_message_source is not None:
            yield self.welcome_message_source

    def make_source_to_page_paths_lookup(self) -> Mapping[Path, Tuple[str, bool]]:
        """
        Make a lookup from source filenames to pages in this site.

        The paths to recipes point to the page containing the native serving
        size for that recipe. Where the boolean part of the mapping values is
        true, this path may be modified to point at other scales and expect to
        find a page at that address. Otherwise, only the listed path will
        exist (e.g. for unscaled recipes).

        Paths to directories point to the unscaled version of the corresponding
        page (i.e. ["categories", ...] path).
        """
        return {
            source: (
                page.path,
                (
                    # Non-recipe pages are always scalable
                    not isinstance(page, RecipePage)
                    # Recipe pages may be scalable, if the recipe is
                    or page.native_servings is not None
                ),
            )
            for page in self.iter_all_pages()
            for source in page.sources()
        }

    def render(
        self,
        source_to_page_paths: Mapping[Path, Tuple[str, bool]],
        filename_to_asset_paths: MutableMapping[Path, str],
    ) -> str:
        welcome_message: str = ""
        if (
            self.welcome_message_html is not None
            and self.welcome_message_source is not None
        ):
            welcome_message = postprocess_html(
                self.welcome_message_html,
                complete_document=False,
                stages=[
                    self.get_resolve_local_links_stage(
                        source=self.welcome_message_source,
                        source_to_page_paths=source_to_page_paths,
                        filename_to_asset_paths=filename_to_asset_paths,
                    )
                ],
            )

        serving_page_hrefs = [
            (num_servings, href.relative(self.path, categories_page.path))
            for num_servings, categories_page in sorted(self.scaled_categories.items())
        ]

        categories_page_href = href.relative(self.path, self.unscaled_categories.path)

        return homepage_template.render(
            welcome_message=welcome_message,
            serving_page_hrefs=serving_page_hrefs,
            categories_page_href=categories_page_href,
            **self.get_template_variables(),
        )


@dataclass
class CategoryPage(Page):
    servings: Optional[int]
    """
    The number of servings selected for this category, or None for native
    number of servings.
    """

    description_html: Optional[str]
    """HTML description."""

    description_source: Optional[Path]
    """The markdown file the description was read from."""

    source_directory: Path
    """The directory representing this category in the original source."""

    subcategories: List["CategoryPage"] = field(default_factory=list)
    """Subcategories, in title-alphabetical order."""

    recipes: List["RecipePage"] = field(default_factory=list, repr=False)
    """Recipes in title-alphabetical order."""

    @classmethod
    def from_directory(
        cls,
        servings: Optional[int],
        directory_path: Path,
        parent: Union[HomePage, "CategoryPage"],
        recipe_pages: MutableMapping[Path, MutableMapping[Optional[int], "RecipePage"]],
    ) -> "CategoryPage":
        """
        Create a category listing page.

        Parameters
        ==========
        servings : int or None
            The number of servings selected. If None, select the native number
            of servings for recipes.
        directory_path : Path
            The directory containing the recipes/subcategories at this level.
        parent: HomePage or CategoryPage
            The parent page in the hierarchy.
        recipe_pages: {recipe_source_path: {servings: MarkdownRecipe, ...}, ...}
            A dictionary which maps from recipe markdown source filenames and
            serving counts (where 'None' is for unscaled recipes with no
            serving count defined) to :py:class:`RecipePage` objects.

            When scaled category pages are generated (i.e. where servings is
            not None), this dictionary will be populated with RecipePage
            objects for the recipes within that category and the given scale.

            When unscaled category pages are generated (i.e. when servings is
            None), this dictionary is used to find the natively scaled
            RecipePage to refer to.

            As a consequence of the above, scaled category pages must be
            created before unscaled ones.
        """
        directory = enumerate_recipe_directory(directory_path)

        root_category = isinstance(parent, HomePage)

        category_page = cls(
            title=(
                directory.title
                if not root_category
                else f"Recipes for {servings}"
                if servings is not None
                else "Categories"
            ),
            parent=parent,
            servings=servings,
            description_html=(
                directory.description_html if not root_category else None
            ),
            description_source=directory.description_source
            if not root_category
            else None,
            source_directory=directory_path,
        )

        category_page.subcategories = sorted(
            (
                CategoryPage.from_directory(
                    servings=servings,
                    directory_path=subdirectory,
                    parent=category_page,
                    recipe_pages=recipe_pages,
                )
                for subdirectory in directory.subdirectories
            ),
            key=lambda p: p.title,
        )

        if servings is not None:
            for recipe_source in directory.recipes:
                scaled_recipe_pages = recipe_pages.setdefault(recipe_source, {})
                recipe_page = RecipePage.from_recipe_source(
                    servings=servings,
                    recipe_source=recipe_source,
                    parent=category_page,
                    other_scalings=scaled_recipe_pages,
                )
                category_page.recipes.append(recipe_page)
        else:
            for recipe_source in directory.recipes:
                this_recipe_pages = recipe_pages[recipe_source]
                if 1 in this_recipe_pages:  # Scalable recipe
                    recipe_page = this_recipe_pages[1]
                else:  # Unscalable recipe
                    recipe_page = this_recipe_pages[None]
                native_servings = recipe_page.native_servings
                try:
                    recipe_page = recipe_pages[recipe_source][native_servings]
                except KeyError:
                    raise MaxServingsLowerThanLargestRecipeError(
                        f"The maximum number of servings must be at least {native_servings}"
                    )
                category_page.recipes.append(recipe_page)

                # Bodge: For unscaled recipes, the native number of servings
                # will be None. Over-write the parent with this (unscaled)
                # categories page.
                if native_servings is None:
                    recipe_page.parent = category_page

        category_page.recipes.sort(key=lambda recipe_page: recipe_page.title)

        return category_page

    @property
    def path(self) -> str:
        assert self.parent is not None  # For type checking purposes
        return (
            href.parent(self.parent.path)
            + "/"
            + (
                self.source_directory.name
                if not isinstance(self.parent, HomePage)
                else (
                    f"serves{self.servings}"
                    if self.servings is not None
                    else "categories"
                )
            )
            + "/index.html"
        )

    def children(self) -> Iterator[Union["CategoryPage", "RecipePage"]]:
        yield from iter(self.subcategories)
        if self.servings is not None:
            yield from iter(self.recipes)

    def sources(self) -> Iterator[Path]:
        if self.servings is None:
            if self.description_source is not None:
                yield self.description_source

            yield self.source_directory

    def render(
        self,
        source_to_page_paths: Mapping[Path, Tuple[str, bool]],
        filename_to_asset_paths: MutableMapping[Path, str],
    ) -> str:
        description: str = ""
        if self.description_html is not None and self.description_source is not None:
            description = postprocess_html(
                self.description_html,
                complete_document=False,
                stages=[
                    self.get_resolve_local_links_stage(
                        source=self.description_source,
                        source_to_page_paths=source_to_page_paths,
                        filename_to_asset_paths=filename_to_asset_paths,
                    )
                ],
            )

        categories = [
            (categories_page.title, href.relative(self.path, categories_page.path))
            for categories_page in self.subcategories
        ]

        recipes = [
            (recipes_page.title, href.relative(self.path, recipes_page.path))
            for recipes_page in self.recipes
        ]

        return categories_template.render(
            description=description,
            categories=categories,
            recipes=recipes,
            **self.get_template_variables(),
        )


@dataclass
class RecipePage(Page):
    servings: Optional[int]
    """Number of servings to scale to (None for unscaled recipes)."""

    native_servings: Optional[int]
    """
    Number of servings the recipe was originally specified for (None for
    unscaled recipes).
    """

    recipe_html: str
    """The rendered recipe HTML."""

    recipe_source: Path
    """The markdown file containing the recipe source."""

    other_scalings: MutableMapping[Optional[int], "RecipePage"]
    """Pages showing this recipe at other scales."""

    @classmethod
    def from_recipe_source(
        cls,
        servings: Optional[int],
        recipe_source: Path,
        parent: CategoryPage,
        other_scalings: MutableMapping[Optional[int], "RecipePage"],
    ) -> "RecipePage":
        """
        The ``other_scalings[servings]`` dictionary entry will be populated
        with the value returned by this function.

        For unscaled recipes (i.e. those without a serving count in the title),
        the 'servings' argument will be ignored and 'None' will be implicitly
        used instead.

        If an other_scalings entry already exists, the existing page will be
        returned (and the 'parent' argument will be ignored). For unscaled
        recipes, this means that repeated calls with different scales will all
        return the same (unscaled) recipe page. This page should later have its
        :py:attr:`parent` attribute replaced with the corresponding unscaled
        category page.
        """
        recipe = compile_recipe_markdown(recipe_source, require_servings=False)

        # Actually checked by compile_recipe_markdown; only here for type
        # checking purposes...
        assert recipe.title is not None

        if recipe.servings is None:
            servings = None
        else:
            # Sanity check
            assert servings is not None

        if servings in other_scalings:
            return other_scalings[servings]
        else:
            recipe_page = RecipePage(
                title=recipe.title,
                parent=parent,
                servings=servings,
                native_servings=recipe.servings,
                recipe_html=recipe.render(
                    Fraction(servings, recipe.servings) if servings is not None else 1
                ),
                recipe_source=recipe_source,
                other_scalings=other_scalings,
            )
            other_scalings[servings] = recipe_page
            return recipe_page

    @property
    def path(self) -> str:
        assert self.parent is not None
        return (
            href.parent(self.parent.path)
            + "/"
            + (self.recipe_source.name.rpartition(".")[0] + ".html")
        )

    def children(self) -> Iterator[Page]:
        return iter(())

    def sources(self) -> Iterator[Path]:
        if self.servings == self.native_servings:
            yield self.recipe_source

    def render(
        self,
        source_to_page_paths: Mapping[Path, Tuple[str, bool]],
        filename_to_asset_paths: MutableMapping[Path, str],
    ) -> str:
        body = postprocess_html(
            self.recipe_html,
            complete_document=False,
            stages=[
                self.get_resolve_local_links_stage(
                    source=self.recipe_source,
                    source_to_page_paths=source_to_page_paths,
                    filename_to_asset_paths=filename_to_asset_paths,
                ),
                partial(
                    add_recipe_scaling_links,
                    from_path=self.path,
                    scaled_paths={
                        num_servings: recipe_page.path
                        for num_servings, recipe_page in self.other_scalings.items()
                    },
                    native_servings=self.native_servings,
                ),
            ],
        )

        return recipe_template.render(
            body=body,
            **self.get_template_variables(),
        )


def generate_static_site(
    input_directory: Path,
    output_directory: Path,
    max_servings: int = 10,
) -> None:
    """
    Generate a static recipe website.

    Parameters
    ==========
    input_directory: Path
        The directory containing recipe grid markdown files.
    output_directory: Path
        The directory to write the generated pages. Will be created if it does
        not exist. Should ideally be empty but if not, existing files will be
        clobbered without warning.
    max_servings: int
        The maximum number of servings to scale a recipe to. Must be at least
        as large as the largest recipe in the site.
    """
    # Generate the site
    home_page = HomePage.from_root_directory(
        root_directory=input_directory,
        max_servings=max_servings,
    )

    # Render and write the pages
    source_to_page_paths = home_page.make_source_to_page_paths_lookup()
    filename_to_asset_paths: MutableMapping[Path, str] = {}
    for page in home_page.iter_all_pages():
        page_html = page.render(
            source_to_page_paths=source_to_page_paths,
            filename_to_asset_paths=filename_to_asset_paths,
        )

        assert page.path[0] == "/"
        page_filename = output_directory / Path(*page.path[1:].split("/"))
        page_filename.parent.mkdir(parents=True, exist_ok=True)
        page_filename.open("w").write(page_html)

    # Create the CSS style sheet
    assert CSS_PATH[0] == "/"
    css_filename = output_directory / Path(*CSS_PATH[1:].split("/"))
    css_filename.parent.mkdir(parents=True, exist_ok=True)
    css_filename.open("w").write(website_css_template.render())

    # Copy in the additional assets
    for asset_source, asset_path in filename_to_asset_paths.items():
        assert asset_path[0] == "/"
        asset_destination = output_directory / Path(*asset_path[1:].split("/"))
        asset_destination.parent.mkdir(parents=True, exist_ok=True)
        copyfile(asset_source, asset_destination)
