import pytest

from typing import cast

from fractions import Fraction

from textwrap import dedent

from peggie import Parser, ParseError

from recipe_grid.parser.grammar import grammar, prettify_parse_error
from recipe_grid.parser.ast import (
    RecipeTransformer,
    Recipe,
    Stmt,
    Step,
    Reference,
    Quantity,
    Proportion,
    String,
    Substring,
    InterpolatedValue,
)


def parse_to_ast(source: str) -> Recipe:
    parser = Parser(grammar)
    try:
        parse_tree = parser.parse(source)
    except ParseError as e:
        raise prettify_parse_error(e)
    return cast(Recipe, RecipeTransformer().transform(parse_tree))


@pytest.mark.parametrize(
    "source, exp_ast",
    [
        # Minimal recipe
        ("spam", Recipe([Stmt(Reference(String("spam")))])),
        # Multiple words
        ("spam and spam", Recipe([Stmt(Reference(String("spam and spam")))])),
        # Quoted string types
        (r"'spam \?\n\' spam'", Recipe([Stmt(Reference(String("spam ?\n' spam")))])),
        (r'"spam \?\n\" spam"', Recipe([Stmt(Reference(String('spam ?\n" spam')))])),
        (r"{spam \?\n\{\} spam}", Recipe([Stmt(Reference(String("spam ?\n{} spam")))])),
        # Concatenated strings
        (
            "{Spam} spam 'and' \"spaM\"",
            Recipe(
                [
                    Stmt(
                        Reference(
                            String(
                                [
                                    Substring(0, "Spam"),
                                    Substring(0, " "),
                                    Substring(0, "spam"),
                                    Substring(0, " "),
                                    Substring(0, "and"),
                                    Substring(0, " "),
                                    Substring(0, "spaM"),
                                ]
                            )
                        )
                    )
                ]
            ),
        ),
        # String interpolation
        (
            "spam {1}",
            Recipe(
                [
                    Stmt(
                        Reference(
                            String(
                                [
                                    Substring(0, "spam"),
                                    Substring(0, " "),
                                    InterpolatedValue(0, 1),
                                ]
                            )
                        )
                    )
                ]
            ),
        ),
        # String interpolation
        (
            "spam {before 1 after 1 2/3 between 1.23 end}",
            Recipe(
                [
                    Stmt(
                        Reference(
                            String(
                                [
                                    Substring(0, "spam"),
                                    Substring(0, " "),
                                    Substring(0, "before "),
                                    InterpolatedValue(0, 1),
                                    Substring(0, " after "),
                                    InterpolatedValue(0, Fraction(5, 3)),
                                    Substring(0, " between "),
                                    InterpolatedValue(0, 1.23),
                                    Substring(0, " end"),
                                ]
                            )
                        )
                    )
                ]
            ),
        ),
        # Proportion (remainder)
        (
            "remaining spam",
            Recipe([Stmt(Reference(String("spam"), Proportion(0, None, False)))]),
        ),
        (
            "remainder spam",
            Recipe([Stmt(Reference(String("spam"), Proportion(0, None, False)))]),
        ),
        (
            "remainder of spam",
            Recipe([Stmt(Reference(String("spam"), Proportion(0, None, False)))]),
        ),
        (
            "rest spam",
            Recipe([Stmt(Reference(String("spam"), Proportion(0, None, False)))]),
        ),
        (
            "rest of spam",
            Recipe([Stmt(Reference(String("spam"), Proportion(0, None, False)))]),
        ),
        # Proportion (%)
        (
            "50% spam",
            Recipe([Stmt(Reference(String("spam"), Proportion(0, 0.5, True)))]),
        ),
        (
            "100/3% spam",
            Recipe(
                [Stmt(Reference(String("spam"), Proportion(0, Fraction(1, 3), True)))]
            ),
        ),
        (
            "100 100/3% spam",
            Recipe(
                [Stmt(Reference(String("spam"), Proportion(0, Fraction(4, 3), True)))]
            ),
        ),
        (
            "25% * spam",
            Recipe([Stmt(Reference(String("spam"), Proportion(0, 0.25, True)))]),
        ),
        # Proportion (factor)
        (
            "0.1 * spam",
            Recipe([Stmt(Reference(String("spam"), Proportion(0, 0.1, False)))]),
        ),
        (
            "2/3 * spam",
            Recipe(
                [Stmt(Reference(String("spam"), Proportion(0, Fraction(2, 3), False)))]
            ),
        ),
        (
            "1 2/3 * spam",
            Recipe(
                [Stmt(Reference(String("spam"), Proportion(0, Fraction(5, 3), False)))]
            ),
        ),
        # Explicit quantity
        (
            "{123} spam",
            Recipe([Stmt(Reference(String("spam"), Quantity(0, 123.0, None)))]),
        ),
        (
            "{123g} spam",
            Recipe([Stmt(Reference(String("spam"), Quantity(0, 123.0, String("g"))))]),
        ),
        (
            "{123 foo bar} spam",
            Recipe(
                [Stmt(Reference(String("spam"), Quantity(0, 123.0, String("foo bar"))))]
            ),
        ),
        (
            "{1.23 kg} spam",
            Recipe([Stmt(Reference(String("spam"), Quantity(0, 1.23, String("kg"))))]),
        ),
        (
            "{2/3 kg} spam",
            Recipe(
                [
                    Stmt(
                        Reference(
                            String("spam"), Quantity(0, Fraction(2, 3), String("kg"))
                        )
                    )
                ]
            ),
        ),
        (
            "{1 2/3 kg} spam",
            Recipe(
                [
                    Stmt(
                        Reference(
                            String("spam"), Quantity(0, Fraction(5, 3), String("kg"))
                        )
                    )
                ]
            ),
        ),
        # Implicit quantity
        (
            "123 spam",
            Recipe([Stmt(Reference(String("spam"), Quantity(0, 123.0, None)))]),
        ),
        (
            "123g spam",
            Recipe([Stmt(Reference(String("spam"), Quantity(0, 123.0, String("g"))))]),
        ),
        (
            "1.23 kg spam",
            Recipe([Stmt(Reference(String("spam"), Quantity(0, 1.23, String("kg"))))]),
        ),
        (
            "2/3 kg spam",
            Recipe(
                [
                    Stmt(
                        Reference(
                            String("spam"), Quantity(0, Fraction(2, 3), String("kg"))
                        )
                    )
                ]
            ),
        ),
        (
            "1 2/3 kg spam",
            Recipe(
                [
                    Stmt(
                        Reference(
                            String("spam"), Quantity(0, Fraction(5, 3), String("kg"))
                        )
                    )
                ]
            ),
        ),
        # Steps
        (
            "cook(spam)",
            Recipe([Stmt(Step(String("cook"), [Reference(String("spam"), None)],))]),
        ),
        (
            "cook(spam,)",
            Recipe([Stmt(Step(String("cook"), [Reference(String("spam"), None)],))]),
        ),
        (
            "cook(spam, eggs)",
            Recipe(
                [
                    Stmt(
                        Step(
                            String("cook"),
                            [
                                Reference(String("spam"), None),
                                Reference(String("eggs"), None),
                            ],
                        )
                    )
                ]
            ),
        ),
        (
            "cook(\nspam,\neggs\n)",
            Recipe(
                [
                    Stmt(
                        Step(
                            String("cook"),
                            [
                                Reference(String("spam"), None),
                                Reference(String("eggs"), None),
                            ],
                        )
                    )
                ]
            ),
        ),
        (
            "cook(spam, eggs, )",
            Recipe(
                [
                    Stmt(
                        Step(
                            String("cook"),
                            [
                                Reference(String("spam"), None),
                                Reference(String("eggs"), None),
                            ],
                        )
                    )
                ]
            ),
        ),
        # Nested steps
        (
            "cook(slice(spam))",
            Recipe(
                [
                    Stmt(
                        Step(
                            String("cook"),
                            [Step(String("slice"), [Reference(String("spam"), None)])],
                        )
                    )
                ]
            ),
        ),
        # Left-to-right syntax
        (
            "spam, slice, cook",
            Recipe(
                [
                    Stmt(
                        Step(
                            String("cook"),
                            [Step(String("slice"), [Reference(String("spam"), None)])],
                        )
                    )
                ]
            ),
        ),
        (
            "(spam, slice, cook)",
            Recipe(
                [
                    Stmt(
                        Step(
                            String("cook"),
                            [Step(String("slice"), [Reference(String("spam"), None)])],
                        )
                    )
                ]
            ),
        ),
        (
            "cook((spam, slice))",
            Recipe(
                [
                    Stmt(
                        Step(
                            String("cook"),
                            [Step(String("slice"), [Reference(String("spam"), None)])],
                        )
                    )
                ]
            ),
        ),
        # Assignment of outputs
        (
            "meat = spam, sliced",
            Recipe(
                [
                    Stmt(
                        Step(String("sliced"), [Reference(String("spam"), None)]),
                        [String("meat")],
                        False,
                    )
                ]
            ),
        ),
        (
            "meat := spam, sliced",
            Recipe(
                [
                    Stmt(
                        Step(String("sliced"), [Reference(String("spam"), None)]),
                        [String("meat")],
                        True,
                    )
                ]
            ),
        ),
        (
            "meat, drained fat = spam, fried and drained",
            Recipe(
                [
                    Stmt(
                        Step(
                            String("fried and drained"),
                            [Reference(String("spam"), None)],
                        ),
                        [String("meat"), String("drained fat")],
                        False,
                    )
                ]
            ),
        ),
        # Multiple recipes
        (
            "spam\neggs",
            Recipe(
                [
                    Stmt(Reference(String("spam"), None)),
                    Stmt(Reference(String("eggs"), None)),
                ]
            ),
        ),
    ],
)
def test_valid_cases(source: str, exp_ast: Recipe) -> None:
    ast = parse_to_ast(source)
    assert ast == exp_ast


@pytest.mark.parametrize(
    "source, exp_error",
    [
        # Empty recipe is not allowed!
        (
            "",
            """
                At line 1 column 1:

                    ^
                Expected <action> or <ingredient> or <quantity>
            """,
        ),
        # Invalid character for name
        (
            ",",
            """
                At line 1 column 1:
                    ,
                    ^
                Expected <action> or <ingredient> or <quantity>
            """,
        ),
        (
            "a = b = c",
            """
                At line 1 column 7:
                    a = b = c
                          ^
                Expected '(' or ',' or <text>
            """,
        ),
        # Incomplete fraction
        (
            "1/ spam",
            """
                At line 1 column 4:
                    1/ spam
                       ^
                Expected <number>
            """,
        ),
        (
            "/2 spam",
            """
                At line 1 column 1:
                    /2 spam
                    ^
                Expected <action> or <ingredient> or <quantity>
            """,
        ),
        (
            "foo\n/2 spam",
            """
                At line 2 column 1:
                    /2 spam
                    ^
                Expected <action> or <ingredient> or <quantity>
            """,
        ),
        # Bad assignment operator
        (
            "foo /= bar",
            """
                At line 1 column 5:
                    foo /= bar
                        ^
                Expected '(' or ',' or '=' or ':=' or <text>
            """,
        ),
        # Trailing comma on assignment
        (
            "foo, bar, = baz",
            """
                At line 1 column 11:
                    foo, bar, = baz
                              ^
                Expected <action> or <output>
            """,
        ),
        # Trailing comma on shorthand
        (
            "foo, bar,",
            """
                At line 1 column 10:
                    foo, bar,
                             ^
                Expected <action> or <output>
            """,
        ),
        (
            "a = foo, bar,",
            """
                At line 1 column 14:
                    a = foo, bar,
                                 ^
                Expected <action>
            """,
        ),
        # Empty inline LTR shorthand
        (
            "()",
            """
                At line 1 column 2:
                    ()
                     ^
                Expected <ingredient> or <quantity>
            """,
        ),
        # Mismatched shorthand brackets
        (
            "(foo",
            """
                At line 1 column 5:
                    (foo
                        ^
                Expected '(' or ')' or ',' or <text>
            """,
        ),
        (
            "foo)",
            """
                At line 1 column 4:
                    foo)
                       ^
                Expected '(' or ',' or '=' or ':=' or <text>
            """,
        ),
        # Empty step
        (
            "foo()",
            """
                At line 1 column 5:
                    foo()
                        ^
                Expected <action> or <ingredient> or <quantity>
            """,
        ),
        (
            "foo(,)",
            """
                At line 1 column 5:
                    foo(,)
                        ^
                Expected <action> or <ingredient> or <quantity>
            """,
        ),
        # Empty input to step
        (
            "foo(bar,,baz)",
            """
                At line 1 column 9:
                    foo(bar,,baz)
                            ^
                Expected ')' or <action> or <ingredient> or <quantity>
            """,
        ),
        # Mismatched step brackets
        (
            "foo(bar",
            """
                At line 1 column 8:
                    foo(bar
                           ^
                Expected '(' or ')' or ',' or <text>
            """,
        ),
        # Ingredient without name
        (
            "500g",
            """
                At line 1 column 5:
                    500g
                        ^
                Expected '(' or ',' or '=' or ':=' or <ingredient> or <text>
            """,
        ),
        # Explicit quantity without closing bracket
        (
            "{",
            """
                At line 1 column 2:
                    {
                     ^
                Expected '}' or <number> or <text>
            """,
        ),
        (
            "{500g nutmeg",
            """
                At line 1 column 13:
                    {500g nutmeg
                                ^
                Expected '}' or <text>
            """,
        ),
        # Mismatched quoted strings
        (
            "'foo",
            """
                At line 1 column 5:
                    'foo
                        ^
                Expected "'" or <text>
            """,
        ),
        (
            '"foo',
            """
                At line 1 column 5:
                    "foo
                        ^
                Expected '"' or <text>
            """,
        ),
        (
            "foo {bar",
            """
                At line 1 column 9:
                    foo {bar
                            ^
                Expected '}' or <text>
            """,
        ),
    ],
)
def test_invalid_cases(source: str, exp_error: str) -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_to_ast(source)
    error = str(exc_info.value)

    assert error == dedent(exp_error).strip()
