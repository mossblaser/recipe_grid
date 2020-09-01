"""
A simple units and measures system.

This system is much less sophisticated than things like :py:mod:`pint` but
consequently easier to understand and use for non-unit-conversion-related
tasks and 'dubious' measures (e.g. 'garlic').
"""

from typing import Optional, Union, List, NamedTuple

from fractions import Fraction

from dataclasses import dataclass

import re


__all__ = [
    "Definition",
    "Unit",
    "RelatedUnitSet",
    "UNITS",
]


Number = Union[int, float, Fraction]


class Definition(NamedTuple):
    quantity: Number
    unit: str


@dataclass
class Unit:
    """Defines a unit of measurement."""

    names: List[str]
    """The name(s) for this unit."""

    definition: Optional[Definition] = None
    """
    For base units, this is None. For all derived units, a quantity and unit
    defining this unit.
    """

    @property
    def name(self) -> str:
        return self.names[0]


@dataclass
class RelatedUnitSet:
    """A collection of related units."""

    units: List[Unit]


UNITS = {
    "mass": RelatedUnitSet(
        [
            # Metric
            Unit(["g", "gram", "grams"]),
            Unit(
                ["kg", "kilo", "kilos", "kilogram", "kilograms"], Definition(1000, "g")
            ),
            # Crazy
            Unit(["lb", "lbs", "pound", "pounds"], Definition(453.59237, "g")),
            Unit(["oz", "ozs", "ounce", "ounces"], Definition(Fraction(1, 16), "lb")),
        ]
    ),
    "volume": RelatedUnitSet(
        [
            # Metric
            Unit(["l", "litre"]),
            Unit(
                ["ml", "mill", "mills", "milliliter", "milliliters"],
                Definition(Fraction(1, 1000), "l"),
            ),
            # Spoons
            Unit(
                ["tsp", "tsps", "teaspoons", "teaspoon", "tea spoon", "tea spoons"],
                Definition(Fraction(5, 1000), "l"),
            ),
            Unit(
                [
                    "tbsp",
                    "tbsps",
                    "tablespoon",
                    "tablespoons",
                    "table spoon",
                    "table spoons",
                ],
                Definition(Fraction(15, 1000), "l"),
            ),
            # Crazy
            Unit(["cup", "cups"], Definition(236.58824, "ml")),
            Unit(["pint", "pints"], Definition(568.261, "ml")),
            # Dubious
            Unit(["can", "cans"], Definition(400, "ml")),
        ]
    ),
    "garlic": RelatedUnitSet(
        [Unit(["clove", "cloves"]), Unit(["bulb", "bulbs"], Definition(10, "cloves"))]
    ),
}
"""
The units known to this system.
"""


ALL_UNITS_REGEX_LITERAL = "|".join(
    re.escape(name)
    for unit_set in UNITS.values()
    for unit in unit_set.units
    for name in unit.names
)
"""
A regex literal which matches any of the unit names defined above.
"""
