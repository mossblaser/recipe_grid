import pytest

from typing import Union

from fractions import Fraction

from recipe_grid.number_formatting import (
    format_float,
    format_fraction,
    format_number,
)


@pytest.mark.parametrize(
    "number, significant_figures, exp_str",
    [
        # Integer values
        (0, 3, "0"),
        (1, 3, "1"),
        (-1, 3, "-1"),
        (12345, 3, "12345"),
        (-12345, 3, "-12345"),
        # Fractions less than 1
        (0.12345, 3, "0.123"),
        # Rounds correctly
        (0.98765, 3, "0.988"),
        # Drops trailing zeros
        (0.10045, 3, "0.1"),
        # Drops decimal if no decimal digits
        (0.00045, 3, "0"),
        # Digits before the decimal reduce number of digits after
        (0.12345, 3, "0.123"),
        (1.2345, 3, "1.23"),
        (12.345, 3, "12.3"),
        (123.45, 3, "123"),
        # Correct rounding when decimal digits are dropped
        (0.9999, 3, "1"),
        (-0.9999, 3, "-1"),
        (123.9999, 3, "124"),
        (-123.9999, 3, "-124"),
        # No significant figures results in rounding to int
        (1.234, 0, "1"),
        (9.876, 0, "10"),
    ],
)
def test_format_float(number: float, significant_figures: int, exp_str: str) -> None:
    assert format_float(number, significant_figures) == exp_str


@pytest.mark.parametrize(
    "number, exp_str",
    [
        # Integer values
        (0, "0"),
        (1, "1"),
        (-1, "-1"),
        (12345, "12345"),
        (-12345, "-12345"),
        (Fraction(10, 1), "10"),
        (Fraction(-10, 1), "-10"),
        (Fraction(10, -1), "-10"),
        # Simple fractions
        (Fraction(1, 2), "1/2"),
        (Fraction(3, 5), "3/5"),
        (Fraction(-3, 5), "-3/5"),
        (Fraction(3, -5), "-3/5"),
        # Improper fractions
        (Fraction(4, 3), "1 1/3"),
        (Fraction(-4, 3), "-1 1/3"),
        (Fraction(4, -3), "-1 1/3"),
        # Fractions more easily understood as decimals
        (Fraction(1, 20), "0.05"),
        (Fraction(-1, 20), "-0.05"),
        (Fraction(1, -20), "-0.05"),
    ],
)
def test_format_fraction(number: Union[int, Fraction], exp_str: str) -> None:
    assert format_fraction(number) == exp_str


@pytest.mark.parametrize(
    "number, exp_str",
    [
        # Integers
        (123, "123"),
        # Floats
        (1.23, "1.23"),
        # Fractions
        (Fraction(3, 5), "3/5"),
    ],
)
def test_format_number(number: Union[int, float, Fraction], exp_str: str) -> None:
    assert format_number(number) == exp_str
