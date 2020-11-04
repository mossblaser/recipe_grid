r"""
Recipe Grid extends Markdown syntax to provide a convenient way of describing
recipes within a document. See the :ref:`markdown_reference` for an overview of
these extensions.

A recipe markdown document is compiled using:

.. autofunction:: compile_markdown

This produces a :py:class:`MarkdownRecipe` object which in turn may be compiled
into a final HTML form using its :py:meth:`MarkdownRecipe.render` method.

.. autoclass:: MarkdownRecipe
    :members:


.. note::

    Unfortunately, though internally Recipe Grid's Markdown parser is built as
    a :py:mod:`marko` extension, due to limitations of the :py:mod:`marko`
    extension API, this extension is not readily composible with other
    extensions. As a result, this extension is not exposed as a public API.

"""

from typing import Optional, List, MutableMapping, Union, Any, NamedTuple, Match, cast

from marko import Markdown, block, inline, helpers  # type: ignore

import re

import random

import string

import html

from fractions import Fraction

from dataclasses import dataclass, field

from collections import OrderedDict

from peggie.error_message_generation import offset_to_line_and_column

from recipe_grid.recipe import Recipe
from recipe_grid.compiler import compile
from recipe_grid.scaled_value_string import ScaledValueString as SVS
from recipe_grid.renderer.html import (
    render_scaled_value_string,
    render_number,
    render_recipe_tree,
    t,
)


def generate_placeholder(num_random_chars: int = 32) -> str:
    """
    Generate a long random ASCII string for use as a unique placeholder
    to temporarily insert into markdown HTML output and later substitute for a
    compiled recipe table.
    """
    slug = "".join(
        random.choice(string.ascii_uppercase) for _ in range(num_random_chars)
    )
    return f"%{slug}%"


class ScaledValueExpression(inline.InlineElement):  # type: ignore
    """
    Marko syntax extension: adds the recipe grid curly-bracket based scalable
    value syntax.
    """

    # Matches fractions, e.g. "1/2" and "3 1/2"
    fraction_pattern = re.compile(
        r"(?:((?P<integer>[0-9]+)[ \t]+)?(?P<numerator>[0-9]+)[ \t]*/[ \t]*(?P<denominator>[0-9]+))"
    )

    # Matches decimal values, e.g. "123" or "1.234"
    decimal_pattern = re.compile(r"(?P<decimal>[0-9]+(\.[0-9]*)?)")

    # Matches a single non-numerical character or backslash escaped character
    free_text_pattern = re.compile(r"\\(?P<escaped_char>.)|(?P<char>[^0-9\{\}])")

    # Matches either a single fraction, decimal or character.
    any_part_pattern = re.compile(
        r"(?:"
        + fraction_pattern.pattern
        + r"|"
        + decimal_pattern.pattern
        + r"|"
        + free_text_pattern.pattern
        + r")"
    )

    # Matches a curly-bracket enclosed string containing fractions and decimals
    # (which should be scaled) and characters (which should be passed through
    # as-is).
    pattern = re.compile(r"\{(?P<source>" + any_part_pattern.pattern + r"*)\}")

    priority = 6

    string: SVS
    """
    The parsed string within the curly brackets as a
    :py;class:`~ScaledValueString`.
    """

    def __init__(self, match: Match[str]) -> None:
        self.string = SVS(
            [
                # Fraction case
                (
                    (int(submatch["integer"]) if submatch["integer"] is not None else 0)
                    + Fraction(
                        int(submatch["numerator"]),
                        int(submatch["denominator"]),
                    )
                )
                if submatch["numerator"] is not None
                else
                # Decimal case
                (
                    int(float(submatch["decimal"]))
                    if "." not in submatch["decimal"]
                    else float(submatch["decimal"])
                )
                if submatch["decimal"] is not None
                else
                # Escaped char case
                submatch["escaped_char"]
                if submatch["escaped_char"] is not None
                else submatch["char"]
                for submatch in self.any_part_pattern.finditer(match["source"])
            ]
        )


class LogPosMixin:
    """
    A mixin for :py:mod:`marko.block` classes which logs the source offset in
    the :py:attr:`pos` attribute when parsing commences ('pos' in marko
    terminology).
    """

    pos: int

    def __init__(self, *args: Any, pos: int, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.pos = pos

    @classmethod
    def parse(cls, source: helpers.Source) -> "LogPosMixin":
        pos = source.pos
        code = super().parse(source)  # type: ignore
        return cls(code, pos=pos)


class CodeBlock(LogPosMixin, block.CodeBlock):  # type: ignore
    """Marko extension: Adds 'pos' attribute to CodeBlock elements."""

    override = True


class FencedCode(LogPosMixin, block.FencedCode):  # type: ignore
    """Marko extension: Adds 'pos' attribute to FencedCode elements."""

    override = True


class Document(block.Document):  # type: ignore
    """
    Marko extension: Makes a copy of the original markdown source in the
    :py:attr:`text` attribute.
    """

    override = True

    text: str
    """
    A copy of the original markdown source provided to Marko.
    """

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.text = text


class RecipeSourceBlock(NamedTuple):
    """
    A named tuple containing details of a recipe-containing source block within
    a Markdown document.
    """

    source: str
    """The recipe listing."""

    pos: int
    """The offset of the start of the recipe listing in the provided markdown."""

    in_fenced_block: bool
    """True if found in fenced code block, False if in an indented block."""

    start_of_new_recipe: bool
    """
    Does this source block mark the beginning of a new, independent recipe
    (with its own separate namespace)?
    """

    def get_line_number_corrected_source(self, markdown_source: str) -> str:
        """
        Return a copy of :py:attr:`source` with newlines prepended such that
        line numbers in the source match the corresponding line numbers in the
        markdown document.

        Requires the complete original markdown source listing (as used during
        parsing) as an argument.
        """
        newlines = "\n" * (offset_to_line_and_column(markdown_source, self.pos)[0] - 1)

        # NB: the 'pos' is the offset of the fence, not the first line of
        # fenced code.
        if self.in_fenced_block:
            newlines += "\n"

        return newlines + self.source


@dataclass
class MarkdownRecipe:
    """
    The result of parsing a recipe grid markdown file.

    Most users should refer directly to the :py:meth:`render` method which will
    produce a complete HTML listing for the recipe, optionally after scaling by
    a given factor. Other metadata (e.g. :py:attr:`title` and
    :py:attr:`servings`) may also be useful for indexing purposes.
    """

    html: str = ""
    """
    The compiled HTML for the markdown document with placeholders for various
    recipe-related values.

    Specifically the following placeholders should be replaced with suitable
    HTML to produce a useful web page:

    * The :py:class:`~ScaledValueString` objects in
      :py:attr:`scaled_value_strings` must be scaled, rendered and substituted
      for the placeholders given in that dictionary. These include places where
      the curly-bracket syntax has been used within a recipe, and the title
      itself when it contains a number of servings.

    * The recipes in :py:attr:`recipe_placeholders` must be scaled and rendered
      as HTML tables and inserted in place of the provided placeholders.

    * When given :py:attr:`pre_title_placeholder` and
      :py:attr:`post_title_placeholder` must be replaced with a suitable
      surroundings for the title-containing H1 tag. For example, a ``<header>``
      tag and the addition of notes about how the recipe was scaled.

    All of the above steps are automated by the :py:meth:`render` method.
    """

    title: Optional[str] = None
    """
    The title of the recipe (with the serving count and prepositions removed,
    if present).

    For example, given the markdown title "# Spam for 2", this field will
    become "Spam".

    If None, no (H1 level) title was given in the recipe.
    """

    servings: Optional[int] = None
    """
    The number of servings this recipe is for, if known from the title.
    """

    pre_title_placeholder: Optional[str] = None
    post_title_placeholder: Optional[str] = None
    """
    Strings which may be substituted with content to insert before and after
    the title-containing <h1>, if one was identified successfully.
    """

    scaled_value_strings: MutableMapping[str, SVS] = field(default_factory=OrderedDict)
    """
    Scaled value strings to be substituted within the recipe text. A mapping
    from placeholder string to corresponding :py:class:`~ScaledValueString`.
    """

    recipe_placeholders: MutableMapping[str, Recipe] = field(
        default_factory=OrderedDict
    )
    """
    Compiled recipes, one per recipe code block, alongside the placeholder
    string.
    """

    @property
    def recipes(self) -> List[List[Recipe]]:
        """
        An convenience view of :py;attr:`recipe_placeholders` containing just
        the recipes without placeholder strings.
        """
        out: List[List[Recipe]] = []
        for recipe in self.recipe_placeholders.values():
            if recipe.follows is None:
                out.append([])
            out[-1].append(recipe)
        return out

    def render(self, scale: Union[int, float, Fraction] = 1) -> str:
        """
        Render this recipe scaled by a given factor.
        """
        html = self.html

        # Substitute scaled value strings
        for placeholder, svs in self.scaled_value_strings.items():
            html = html.replace(
                placeholder,
                render_scaled_value_string(svs.scale(scale)),
            )

        # Substitute scaled recipes
        id_prefix_index = 0
        for placeholder, recipe in self.recipe_placeholders.items():
            if recipe.follows is None:
                id_prefix_index += 1

            if id_prefix_index > 1:
                id_prefix = f"recipe{id_prefix_index}-"
            else:
                id_prefix = "recipe-"

            html = html.replace(
                placeholder,
                t(
                    "div",
                    "\n".join(
                        render_recipe_tree(recipe_tree, id_prefix)
                        for recipe_tree in recipe.scale(scale).recipe_trees
                    ),
                    class_="rg-recipe-block",
                ),
            )

        # Modify heading to include scaling info
        if (
            self.title is not None
            and self.pre_title_placeholder is not None
            and self.post_title_placeholder is not None
        ):
            html = html.replace(self.pre_title_placeholder, "<header>")
            post_title_text = ""
            if scale != 1:
                if self.servings is not None:
                    orig_servings = t(
                        "span",
                        f"{self.servings} serving{'s' if self.servings != 1 else ''}",
                        class_="rg-original-servings",
                    )
                    post_title_text = t("p", f"Rescaled from {orig_servings}.")
                else:
                    scale_str = t(
                        "span",
                        f"{render_number(scale)}&times;",
                        class_="rg-scaling-factor",
                    )
                    post_title_text = t("p", f"Scaled {scale_str}")
            html = html.replace(
                self.post_title_placeholder, f"{post_title_text}</header>"
            )

        return html


class RecipeGridRendererMixin:
    """
    Mixin for :py:class:`marko.renderer.Renderer` which collects recipe code
    blocks, and the input markdown source, during rendering.

    Indented code blocks and code blocks fenced code blocks with language
    ``recipe`` or ``new-recipe`` are treated as recipe blocks and extracted.
    All other blocks are treated as ordinary code blocks and left to the
    renderer.
    """

    title_serving_count_pattern = re.compile(
        (
            r"(?P<preposition>((to\s+)?serves?|for|makes|serving)\s+)"
            r"(?P<servings>[0-9]+)\s*"
            r"$"
        ),
        re.IGNORECASE,
    )
    """
    A regex matching recipe a preposition and serving count (e.g. in "Spam for
    2" finding "for " and "2" respectively).

    .. note::

        This regular expression does not include a match field for the rest of
        the title since Python's regex parser works left-to-right trying to
        find the longest match possible. As a consequence if we added a
        ``(?P<title>.*)`` to the start, we would potentially end up with some
        optional leading parts of a preposition stuck in the title.
    """

    output: MarkdownRecipe
    """
    The parsed markdown recipe structure, populated during rendering and
    returned as the final render result.
    """

    independent_recipe_source_blocks: List[MutableMapping[str, RecipeSourceBlock]]
    """
    Accumulates :py:class:`RecipeSourceBlock` tuples corresponding with recipe
    source blocks in the markdown source.

    The outer list groups the blocks into consecutive series of blocks starting
    with a ``new-recipe`` fenced block (or starting with the first recipe block
    in the file).

    The inner mappings are :py:class:`OrderedDict` objects mapping from
    placeholder strings to :py:class:`RecipeSourceBlock` tuples.
    """

    first_heading: bool
    """
    A flag cleared after the first heading in the source has been rendered.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore

        self.output = MarkdownRecipe()
        self.independent_recipe_source_blocks = []
        self.first_heading = True

    def render_heading(self, element: block.Heading) -> str:
        """
        Render headings, also capturing the first heading if it contains a
        serving count.
        """
        level = element.level
        text = self.render_children(element)  # type: ignore

        pre = ""  # To prepend before <h*> tag
        post = ""  # To append after </h*> tag
        attrs = ""  # Attributes to be inserted into the <h*> tag.

        # Capture the first title as recipe title. Ignore it if it isn't a H1
        # level title or if it contains HTML or a scaled value substitution
        # since we can't easily turn these into a plain text title.
        if self.first_heading and level == 1 and "<" not in text and "%" not in text:
            match = self.title_serving_count_pattern.search(text)
            if match is None:
                self.output.title = html.unescape(text.strip())
                attrs = ' class="rg-title-unscalable"'
            else:
                title = text[: match.start()]
                self.output.title = html.unescape(title.strip())
                self.output.servings = int(match["servings"])
                placeholder = generate_placeholder()
                self.output.scaled_value_strings[placeholder] = SVS(
                    int(match["servings"])
                )
                text = title + t(
                    "span",
                    match["preposition"] + placeholder,
                    class_="rg-serving-count",
                )
                attrs = ' class="rg-title-scalable"'
            pre = self.output.pre_title_placeholder = generate_placeholder()
            post = self.output.post_title_placeholder = generate_placeholder()

        self.first_heading = False

        return f"{pre}<h{level}{attrs}>{text}</h{level}>{post}\n"

    def render_scaled_value_expression(self, element: ScaledValueExpression) -> str:
        """Render scaled value expressions."""
        placeholder = generate_placeholder()
        self.output.scaled_value_strings[placeholder] = element.string
        return placeholder

    def render_recipe_source_block(
        self,
        element: Union[CodeBlock, FencedCode],
        in_fenced_block: bool,
    ) -> str:
        """
        Substitute recipe-containing code blocks with placeholders, capturing
        the recipe code.
        """
        # Capture the recipe
        recipe_source_block = RecipeSourceBlock(
            source=element.children[0].children,
            pos=element.pos,
            in_fenced_block=in_fenced_block,
            start_of_new_recipe=element.lang == "new-recipe",
        )

        # Start a new independent recipe if required
        if (
            recipe_source_block.start_of_new_recipe
            or len(self.independent_recipe_source_blocks) == 0
        ):
            self.independent_recipe_source_blocks.append(OrderedDict())

        placeholder = generate_placeholder()
        self.independent_recipe_source_blocks[-1][placeholder] = recipe_source_block

        return placeholder

    def render_code_block(self, element: CodeBlock) -> str:
        """Treat all indented code blocks as a recipe source block."""
        return self.render_recipe_source_block(element, False)

    def render_fenced_code(self, element: FencedCode) -> str:
        """
        Treat fenced code blocks with 'recipe' or 'new-recipe' as recipe source
        blocks. Others are treated as code as usual
        """
        if element.lang in ("recipe", "new-recipe"):
            return self.render_recipe_source_block(element, True)
        else:
            return super().render_fenced_code(element)  # type: ignore

    def render_document(self, element: Document) -> MarkdownRecipe:
        """Render the document and compile all recipe code blocks."""
        # Render the markdown document
        self.output.html = super().render_children(element)  # type: ignore

        # Compile captured recipe blocks
        markdown_source = element.text
        for recipe_source_blocks in self.independent_recipe_source_blocks:
            placeholders = list(recipe_source_blocks.keys())
            sources = [
                recipe_source_block.get_line_number_corrected_source(markdown_source)
                for recipe_source_block in recipe_source_blocks.values()
            ]
            recipes = compile(sources)
            for placeholder, recipe in zip(placeholders, recipes):
                self.output.recipe_placeholders[placeholder] = recipe

        return self.output


class RecipeGrid:
    """
    A :py:mod:`marko` extension which causes the renderer to output a
    :py:class:`MarkdownRecipe` object containing the parsed recipe grid
    markdown document ready to later be scaled and rendered as final HTML.
    """

    elements = [ScaledValueExpression, Document, CodeBlock, FencedCode]
    renderer_mixins = [RecipeGridRendererMixin]


def compile_markdown(markdown_source: str) -> MarkdownRecipe:
    """
    Compile a recipe grid flavoured markdown document, producing a
    :py:class:`MarkdownRecipe` which may be rescaled and rendered into the
    final HTML form as required.

    Internally calls :py:func:`recipe_grid.compiler.compile` and so may throw
    the same kinds of exceptions when syntax errors in the recipe sources are
    encountered.
    """
    return cast(MarkdownRecipe, Markdown(extensions=[RecipeGrid])(markdown_source))
