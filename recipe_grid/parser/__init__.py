"""
The recipe description language is parsed into an Abstract Syntax Tree
(AST) using :py:func:`recipe_grid.parser.parse`:

.. autofunction:: recipe_grid.parser.parse
"""

from typing import cast

from peggie import Parser, ParseError

from recipe_grid.parser.grammar import grammar, prettify_parse_error

from recipe_grid.parser import ast


def parse(source: str) -> ast.Recipe:
    """
    Parse a recipe into an AST (see :py:mod:`recipe_grid.parser.ast`).

    Raises
    ======
    peggie.ParseError
    """
    parser = Parser(grammar)
    try:
        parse_tree = parser.parse(source)
    except ParseError as e:
        raise prettify_parse_error(e)
    return cast(ast.Recipe, ast.RecipeTransformer().transform(parse_tree))
