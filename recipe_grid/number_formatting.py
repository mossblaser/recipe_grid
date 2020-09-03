"""
Human-friendly relatively concise number formatting routines.

At a high-level the following function may be used:

.. autofunction:: format_number

Though this in turn is implemented by the following specialised functions

.. autofunction:: format_float

.. autofunction:: format_fraction
"""

import math

from typing import Callable, Union, FrozenSet

from fractions import Fraction


__all__ = [
    "format_float",
    "format_fraction",
    "format_number",
]


def format_float(number: float, significant_figures: int = 3) -> str:
    """
    Format a floating point value in a concise, human-friendly way.

    This formatter will show up to ``significant_figures`` digits after the
    decimal point, with fewer digits being shown for each significant digit in
    the integer part.

    Trailing zeros after the decimal point are dropped, along with the trailing
    decimal point.

    Scientific notation is never used for large values. Significant digits
    before the decimal point are never dropped.
    """
    fractional, integer = math.modf(number)
    integer_str = f"{integer:.0f}"

    integer_digits = len(integer_str.lstrip("-0"))
    fractional_digits = max(0, significant_figures - integer_digits)
    fractional_abs = abs(fractional)
    fractional_str = f"{fractional_abs:.{fractional_digits}f}"[2:].rstrip("0")

    if len(fractional_str) == 0:
        return str(round(number))

    if fractional_str:
        return f"{integer_str}.{fractional_str}"
    else:
        return integer_str


def format_fraction(
    number: Union[int, Fraction],
    allowed_denominators: FrozenSet[int] = frozenset([2, 3, 4, 5, 6, 7, 8, 12, 16]),
    format_float: Callable[[float], str] = format_float,
) -> str:
    """
    Format a :py:class:`~fractions.Fraction` in a human-friendly way.

    Improper fractions are broken down into an integer and fractional part.

    Fractions whose denominator does not appear in ``allowed_denominators`` are
    instead shown as decimal numbers. Formatting of these is deferred to
    the ``format_float`` function which defaults to :py:func:`format_float`.

    Fractions are rendered as ASCII strings in the style '3/4' or, for improper
    fractions, '1 3/4'.
    """
    if number.denominator == 1:  # Integer case
        return str(number.numerator)
    elif number.denominator not in allowed_denominators:  # Decimal fallback case
        return format_float(float(number))
    elif abs(number.numerator) > number.denominator:  # Improper fraction case
        numerator = number.numerator
        denominator = number.denominator

        sign = -1 if numerator < 0 else 1
        numerator = abs(numerator)

        integer_part = numerator // denominator
        numerator %= denominator

        return f"{sign * integer_part} {numerator}/{denominator}"
    else:  # Ordinary fraction case
        return f"{number.numerator}/{number.denominator}"


def format_number(
    number: Union[float, int, Fraction],
    format_float: Callable[[float], str] = format_float,
    format_fraction: Callable[[Fraction], str] = format_fraction,
) -> str:
    """
    Format a number in a human-friendly way.

    If a fraction is given it will be rendered as a fraction, if it is sensible
    to do so. Otherwise, the number will be represented in decimal form.

    See :py:func:`format_float` and :py:func:`format_fraction`.
    """
    if isinstance(number, float):
        return format_float(number)
    else:
        return format_fraction(number)
