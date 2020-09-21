"""
Routines for parsing Markdown with embedded recipe descriptions.
"""

from typing import List, MutableMapping, Union, Any, NamedTuple, cast

from marko import block, helpers  # type: ignore

from collections import OrderedDict

from peggie.error_message_generation import offset_to_line_and_column


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
    """Adds 'pos' attribute."""

    override = True


class FencedCode(LogPosMixin, block.FencedCode):  # type: ignore
    """Adds 'pos' attribute."""

    override = True


class Document(block.Document):  # type: ignore
    """
    Makes a copy of the original markdown source in the :py:attr:`text`
    attribute.
    """

    override = True

    text: str

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.text = text


class RecipeSourceBlock(NamedTuple):
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
        """
        newlines = "\n" * (offset_to_line_and_column(markdown_source, self.pos)[0] - 1)

        # NB: the 'pos' is the offset of the fence, not the first line of
        # fenced code.
        if self.in_fenced_block:
            newlines += "\n"

        return newlines + self.source


class RecipeGridBaseRendererMixin:
    """
    Base mixin for :py:class:`marko.renderer.Renderer` which collects recipe
    code blocks during rendering.

    The :py:meth:`render_recipe_source_block` method should be implemented
    which provides a (unique) substitution string for recipe code blocks.

    Indented code blocks and code blocks fenced code blocks with language
    ``recipe`` or ``new-recipe`` are treated as recipe blocks and extracted.
    All other blocks are treated as ordinary code blocks and left to the
    renderer.
    """

    independent_recipe_source_blocks: List[MutableMapping[str, RecipeSourceBlock]]
    """
    Contains all the :py:class:`RecipeSourceBlock` tuples corresponding with
    recipe source blocks in the markdown source.

    The outer list groups the blocks into consecutive series of blocks starting
    with a ``new-recipe`` fenced block (or starting with the first recipe block
    in the file).

    The inner mappings are :py:class:`OrderedDict` objects mapping from
    corresponding :py:meth:`render_recipe_source_block` call outputs to
    :py:class:`RecipeSourceBlock` tuples.
    """

    markdown_source: str
    """The full markdown source listing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.independent_recipe_source_blocks = []

    def render_recipe_source_block(self, element: RecipeSourceBlock) -> str:
        raise NotImplementedError()

    def _render_recipe_source_block(
        self, element: Union[CodeBlock, FencedCode], in_fenced_block: bool,
    ) -> str:
        recipe_source_block = RecipeSourceBlock(
            source=element.children[0].children,
            pos=element.pos,
            in_fenced_block=in_fenced_block,
            start_of_new_recipe=element.lang == "new-recipe",
        )
        rendered = self.render_recipe_source_block(recipe_source_block)

        if (
            recipe_source_block.start_of_new_recipe
            or len(self.independent_recipe_source_blocks) == 0
        ):
            self.independent_recipe_source_blocks.append(OrderedDict())
        self.independent_recipe_source_blocks[-1][rendered] = recipe_source_block

        return rendered

    def render_code_block(self, element: CodeBlock) -> str:
        return self._render_recipe_source_block(element, False)

    def render_fenced_code(self, element: FencedCode) -> str:
        if element.lang in ("recipe", "new-recipe"):
            return self._render_recipe_source_block(element, True)
        else:
            return cast(str, super().render_fenced_code(element))  # type: ignore

    def render_document(self, element: Document) -> str:
        final_output = super().render_children(element)  # type: ignore
        self.markdown_source = element.text
        return cast(str, final_output)
