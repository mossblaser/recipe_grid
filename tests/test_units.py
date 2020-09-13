import pytest

import re

from fractions import Fraction

from recipe_grid.units import (
    Number,
    UNIT_SYSTEM,
    ALL_UNITS_REGEX_LITERAL,
)


def test_no_duplicate_names() -> None:
    names = set()
    for related_unit_set in UNIT_SYSTEM.unit_sets.values():
        for name in related_unit_set.iter_names():
            assert name not in names
            names.add(name)


def test_all_units_regex_literal() -> None:
    regex = re.compile(ALL_UNITS_REGEX_LITERAL)
    for name in UNIT_SYSTEM.iter_names():
        assert regex.match(name) is not None
        assert regex.match(name.replace(" ", "    ")) is not None


@pytest.mark.parametrize(
    "from_unit, to_unit, exp",
    [
        # Identity (root)
        ("g", "g", 1),
        # Identity (non-root)
        ("oz", "oz", 1),
        # Parent/child (also using fractions where integers are involved)
        ("g", "kg", Fraction(1, 1000)),
        # Child/parent
        ("kg", "g", 1000),
        # Keeping fractions where given
        ("lb", "oz", 16),
        ("oz", "lb", Fraction(1, 16)),
        # Up and down the tree (also using floats when necessary)
        ("lb", "kg", 453.59237 / 1000.0),
        ("kg", "lb", 1000.0 / 453.59237),
        # Using alternative names
        ("kilos", "grams", 1000),
    ],
)
def test_convert_between(from_unit: str, to_unit: str, exp: Number) -> None:
    assert UNIT_SYSTEM["mass"].convert_between(from_unit, to_unit) == exp
    assert UNIT_SYSTEM.convert_between(from_unit, to_unit) == exp
