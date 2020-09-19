"""
The :py:mod:`peggie` grammar for the recipe specification (read form
``grammar.peg``.

.. autodata:: grammar

.. autodata:: grammar_source

"""

import os

from peggie import compile_grammar, ParseError, RuleExpr, RegexExpr

from recipe_grid.units import ALL_UNITS_REGEX_LITERAL

__all__ = [
    "grammar",
    "grammar_source",
    "prettify_parse_error",
]

grammar_source_path = os.path.join(os.path.dirname(__file__), "grammar.peg")

with open(grammar_source_path) as f:
    grammar_source = f.read().replace("@KNOWN_UNITS@", ALL_UNITS_REGEX_LITERAL)
    """
    The recipe syntax :py:mod:`peggie` grammar source in a string.
    """

grammar = compile_grammar(grammar_source)
"""
The compiled :py:class:`peggie.Grammar` for the recipe syntax.
"""


def prettify_parse_error(parse_error: ParseError) -> ParseError:
    parse_error.expr_explanations = {
        RuleExpr("recipe"): "<action> or <ingredient> or <quantity>",
        RuleExpr("stmt"): "<action> or <ingredient> or <quantity>",
        RuleExpr("ltr_shorthand"): "<ingredient> or <quantity>",
        RuleExpr("expr"): "<action> or <ingredient> or <quantity>",
        RuleExpr("output"): "<output>",
        RuleExpr("action"): "<action>",
        RuleExpr("ingredient"): "<ingredient>",
        RuleExpr("eol"): "<newline>",
        RuleExpr("eof"): "<end of file>",
        RuleExpr("number"): "<number>",
        RuleExpr("interpolated_number"): "<text>",
        RuleExpr("string"): "<text>",
        RuleExpr("static_string"): "<text>",
        RuleExpr("freeform_unit"): "<text>",
        # Add regex descriptions
        RegexExpr("[0-9]+"): "<number>",
        RegexExpr("[^0-9{}\n\r]"): "<text>",
        RegexExpr('[^"\n\r]'): "<text>",
        RegexExpr("[^'\n\r]"): "<text>",
        RegexExpr(":?="): "'=' or ':='",
        # Display literals without escapes
        RegexExpr.literal("("): "'('",
        RegexExpr.literal(")"): "')'",
        RegexExpr.literal(","): "','",
        RegexExpr.literal("{"): "'{'",
        RegexExpr.literal("}"): "'}'",
        RegexExpr.literal("*"): "'*'",
        RegexExpr.literal("%"): "'%'",
        # Omit insignificant whitespace
        RuleExpr("hsp"): None,
        RuleExpr("sp"): None,
    }
    parse_error.last_resort_exprs = {
        RuleExpr("eof"),
        RuleExpr("eol"),
        RegexExpr(r"\\"),
    }
    return parse_error
