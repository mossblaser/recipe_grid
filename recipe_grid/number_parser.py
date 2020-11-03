from typing import Union

import re

from fractions import Fraction


fraction_pattern = re.compile(
    r"((?P<integer>[0-9]+)[ \t]+)?(?P<numerator>[0-9]+)[ \t]*/[ \t]*(?P<denominator>[0-9]+)"
)


def number(value: str) -> Union[int, float, Fraction]:
    """
    Attempt to parse a number formatted as a fraction (e.g. 9 3/4) float (e.g.
    3.14) or integer (e.g. 123). Throws a :py:exc:`ValueError` if this fails.
    """
    match = fraction_pattern.fullmatch(value)
    if match is not None:
        integer = int(match["integer"]) if match["integer"] is not None else 0
        numerator = int(match["numerator"])
        denominator = int(match["denominator"])
        return integer + Fraction(numerator, denominator)
    else:
        try:
            return int(value)
        except ValueError:
            return float(value)
