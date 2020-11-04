import pytest

from typing import Union, Sequence, Tuple

from fractions import Fraction

from recipe_grid.scaled_value_string import Number, ScaledValueString


@pytest.mark.parametrize(
    "arg, exp",
    [
        # Empty string
        ("", ()),
        ([], ()),
        # Just a string
        ("foo", ("foo",)),
        # Just a number
        (123, (123,)),
        # A singleton list
        (["foo"], ("foo",)),
        ([123], (123,)),
        # Adjacent strings should be merged
        (["foo", "bar"], ("foobar",)),
        # Numbers should be allowed to be interspersed with strings
        ([123, "foo", "bar"], (123, "foobar")),
        (["foo", 123, "bar"], ("foo", 123, "bar")),
        (["foo", "bar", 123], ("foobar", 123)),
        # Adjacent numbers should not be merged in any way...
        ([1, 2.0, Fraction(3, 1)], (1, 2.0, Fraction(3, 1))),
        # Empty strings should be removed
        (["", 123, ""], (123,)),
    ],
)
def test_constructor(
    arg: Union[str, Number, Sequence[Union[str, Number]]],
    exp: Tuple[Union[str, Number], ...],
) -> None:
    svs = ScaledValueString(arg)
    assert svs._string == exp


@pytest.mark.parametrize(
    "arg, exp",
    [
        # Just a string
        ("", ""),
        ("foo", "foo"),
        # Just a number
        (123, "123"),
        (Fraction(4, 3), "1 1/3"),  # NB: Fancy formatting from number_formatting
        # Combination of numbers and strings
        (
            ["Hello ", 123, " world ", Fraction(4, 3), "! ", 1, 2, 3.0],
            "Hello 123 world 1 1/3! 123",
        ),  # NB: Fancy formatting from number_formatting
    ],
)
def test_render(
    arg: Union[str, Number, Sequence[Union[str, Number]]],
    exp: str,
) -> None:
    svs = ScaledValueString(arg)
    assert svs.render() == exp
    assert str(svs) == exp


def test_render_custom_formatters() -> None:
    svs = ScaledValueString(["foo", 123])
    assert (
        svs.render(
            format_number=lambda n: str(-n),
            format_string=lambda s: s.upper(),
        )
        == "FOO-123"
    )


@pytest.mark.parametrize(
    "a, b, exp_equal",
    [
        # Empty
        (ScaledValueString([]), ScaledValueString([]), True),
        # Just strings
        (ScaledValueString("foo"), ScaledValueString("foo"), True),
        (ScaledValueString("foo"), ScaledValueString("bar"), False),
        # Just numbers
        (ScaledValueString(123), ScaledValueString(123), True),
        (ScaledValueString(123.0), ScaledValueString(123), True),
        (ScaledValueString(123), ScaledValueString(321), False),
        # Combination
        (ScaledValueString(["foo", 1]), ScaledValueString(["foo", 1]), True),
        (ScaledValueString(["foo", 1]), ScaledValueString(["bar", 1]), False),
        (ScaledValueString(["foo", 1]), ScaledValueString(["foo", 2]), False),
        (ScaledValueString("foo1"), ScaledValueString(["foo", 1]), False),
    ],
)
def test_eq(a: ScaledValueString, b: ScaledValueString, exp_equal: bool) -> None:
    assert (a == b) is exp_equal


@pytest.mark.parametrize(
    "string, mul, exp",
    [
        # No numbers
        (ScaledValueString(), 10, ScaledValueString()),
        (ScaledValueString("foo"), 10, ScaledValueString("foo")),
        # Just numbers
        (ScaledValueString(123), 10, ScaledValueString(1230)),
        # Combination
        (ScaledValueString(["foo", 123]), 10, ScaledValueString(["foo", 1230])),
    ],
)
def test_scale(string: ScaledValueString, mul: Number, exp: ScaledValueString) -> None:
    assert string.scale(mul) == exp


@pytest.mark.parametrize(
    "a, b, exp",
    [
        # Add empty
        (ScaledValueString("foo"), "", ScaledValueString("foo")),
        (ScaledValueString("foo"), ScaledValueString(), ScaledValueString("foo")),
        # Add string
        (ScaledValueString("foo"), "bar", ScaledValueString("foobar")),
        (ScaledValueString(123), "bar", ScaledValueString([123, "bar"])),
        # Add numbers
        (ScaledValueString("foo"), 123, ScaledValueString(["foo", 123])),
        # Add ScaledValueString
        (
            ScaledValueString("foo"),
            ScaledValueString("bar"),
            ScaledValueString("foobar"),
        ),
    ],
)
def test_concat(
    a: ScaledValueString,
    b: Union[str, Number, ScaledValueString],
    exp: ScaledValueString,
) -> None:
    assert (a + b) == exp


def test_lower() -> None:
    assert ScaledValueString(["Foo", 123]).lower() == ScaledValueString(["foo", 123])


def test_upper() -> None:
    assert ScaledValueString(["Foo", 123]).upper() == ScaledValueString(["FOO", 123])


def test_lstrip() -> None:
    assert ScaledValueString(["  Foo ", 123]).lstrip() == ScaledValueString(
        ["Foo ", 123]
    )
    assert ScaledValueString([123, "  Foo "]).lstrip() == ScaledValueString(
        [123, "  Foo "]
    )


def test_rstrip() -> None:
    assert ScaledValueString(["  Foo ", 123]).rstrip() == ScaledValueString(
        ["  Foo ", 123]
    )
    assert ScaledValueString([123, "  Foo "]).rstrip() == ScaledValueString(
        [123, "  Foo"]
    )


def test_strip() -> None:
    assert ScaledValueString(["  Foo ", 123]).strip() == ScaledValueString(
        ["Foo ", 123]
    )
    assert ScaledValueString([123, "  Foo "]).strip() == ScaledValueString(
        [123, "  Foo"]
    )
    assert ScaledValueString(["  Foo "]).strip() == ScaledValueString(["Foo"])
