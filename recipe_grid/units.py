"""
Recipe Grid has a simple understanding of various cooking-related units and can
perform simple conversions between units of the same kind. The complete list of
units is:

.. rgunitbreakdown::

Conversions are possible betweeen units in the same sublist and names listed
together are aliases for one another.

.. note::

    This system is much less sophisticated than things like :py:mod:`pint` but
    consequently easier to understand and use for non-unit-conversion-related
    tasks and also for less conventional measures (e.g. 'cloves').

Internal API
------------

The Unit system is available in the :py:data:`recipe_grid.units.UNIT_SYSTEM`
which is an instance of the following class:

.. autoclass:: recipe_grid.units.UnitSystem
    :members:
"""

from typing import (
    Optional,
    Union,
    List,
    NamedTuple,
    Set,
    Tuple,
    Mapping,
    MutableMapping,
    Iterable,
    Iterator,
)

from fractions import Fraction

from dataclasses import dataclass, field

import re


__all__ = [
    "Definition",
    "Unit",
    "RelatedUnitSet",
    "UNIT_SYSTEM",
]


Number = Union[int, float, Fraction]


class Definition(NamedTuple):
    quantity: Number
    unit: str


@dataclass(frozen=True)
class Unit:
    """Defines a unit of measurement."""

    names: Tuple[str, ...]
    """The name(s) for this unit."""

    definition: Optional[Definition] = None
    """
    For base units, this is None. For all derived units, a quantity and unit
    defining this unit.
    """

    @property
    def name(self) -> str:
        return self.names[0]

    def __contains__(self, name: str) -> bool:
        """Check if a unit name matches this unit."""
        return name in self.names


@dataclass
class UnitTreeNode:
    """
    For internal use by :py:class:`RelatedUnitSet`. A node in a tree of unit
    definitions.
    """

    name: str

    definition: Optional[Tuple[Number, "UnitTreeNode"]]
    """
    The unit this unit is defined in terms of, along with the quantity of this
    unit amounting to one of the parent unit.
    """

    defines: List["UnitTreeNode"] = field(default_factory=list)
    """
    References to all units defined in terms of this node.
    """


class RelatedUnitSet:
    """A collection of related units."""

    units: List[Unit]

    _name_to_node: MutableMapping[str, UnitTreeNode]

    def __init__(self, units: Iterable[Unit]):
        self.units = list(units)
        self._name_to_node = {}
        for i, unit in enumerate(self.units):
            node: UnitTreeNode
            node_definition: Optional[Tuple[Number, UnitTreeNode]]

            if i == 0:
                if unit.definition is not None:
                    raise ValueError(
                        f"The first Unit, {unit}, must have no definition."
                    )
                node = UnitTreeNode(unit.name, None)
            else:
                if unit.definition is None:
                    raise ValueError(f"Unit, {unit} has no definition.")
                parent_node = self._name_to_node[unit.definition.unit]
                node = UnitTreeNode(unit.name, (unit.definition.quantity, parent_node))
                parent_node.defines.append(node)

            for name in unit.names:
                self._name_to_node[name] = node

    def normalise_unit_name(self, name: str) -> str:
        return self._name_to_node[name].name

    def iter_names(self) -> Iterator[str]:
        return iter(self._name_to_node.keys())

    def __contains__(self, name: str) -> bool:
        """Check if a unit name is defined in this set."""
        return name in self._name_to_node

    def iter_conversions_from(self, from_unit: str) -> Iterator[Tuple[Number, str]]:
        """
        Iterate over all possible conversions from the provided unit to all
        other units in this :py:class:`RelatedUnitSet`.
        """
        visited: Set[str] = set()

        # Queue of (factor, node) tuples
        to_visit: List[Tuple[Number, UnitTreeNode]] = [
            (Fraction(1), self._name_to_node[from_unit])
        ]
        while to_visit:
            scale, node = to_visit.pop(0)

            if node.name in visited:
                continue
            visited.add(node.name)

            yield (scale, node.name)

            if node.definition is not None:
                def_scale, def_node = node.definition
                to_visit.append((scale * def_scale, def_node))

            for child_node in node.defines:
                assert child_node.definition is not None  # Always true when a child
                child_scale = child_node.definition[0]
                to_visit.append((scale / child_scale, child_node))

    def convert_between(self, from_unit: str, to_unit: str) -> Number:
        """
        Find the multiplicative conversion factor to convert from one unit
        to another.
        """
        from_unit = self.normalise_unit_name(from_unit)
        to_unit = self.normalise_unit_name(to_unit)
        for scale, unit in self.iter_conversions_from(from_unit):
            if unit == to_unit:
                return scale
        assert False  # Should be unreachable


@dataclass
class UnitSystem:
    """
    A container of unit conversions.
    """

    unit_sets: Mapping[str, RelatedUnitSet]

    _name_to_unit_set: Mapping[str, RelatedUnitSet] = field(init=False)

    def __post_init__(self) -> None:
        self._name_to_unit_set = {
            name: unit_set
            for unit_set in self.unit_sets.values()
            for name in unit_set.iter_names()
        }

    def __getitem__(self, kind: str) -> RelatedUnitSet:
        return self.unit_sets[kind]

    def __contains__(self, unit_name: str) -> bool:
        """Check if a unit name is supported."""
        return unit_name in self._name_to_unit_set

    def iter_names(self) -> Iterator[str]:
        """Iterate over all defined unit names and aliases."""
        return iter(self._name_to_unit_set.keys())

    def iter_conversions_from(self, from_unit: str) -> Iterator[Tuple[Number, str]]:
        """
        Iterate over all possible conversions from the provided unit to all
        other compatible units. Iterates over pairs of multiplicative
        conversion factor and other unit names.
        """
        return self._name_to_unit_set[from_unit].iter_conversions_from(from_unit)

    def convert_between(self, from_unit: str, to_unit: str) -> Number:
        """
        Find the multiplicative conversion factor to convert from one unit
        to another.
        """
        return self._name_to_unit_set[from_unit].convert_between(from_unit, to_unit)


UNIT_SYSTEM = UnitSystem(
    {
        "mass": RelatedUnitSet(
            [
                # Metric
                Unit(("g", "gram", "grams")),
                Unit(
                    ("kg", "kilo", "kilos", "kilogram", "kilograms"),
                    Definition(1000, "g"),
                ),
                # Crazy
                Unit(("lb", "lbs", "pound", "pounds"), Definition(453.59237, "g")),
                Unit(
                    ("oz", "ozs", "ounce", "ounces"), Definition(Fraction(1, 16), "lb")
                ),
            ]
        ),
        "volume": RelatedUnitSet(
            [
                # Metric
                Unit(("l", "litre")),
                Unit(
                    ("ml", "mill", "mills", "milliliter", "milliliters"),
                    Definition(Fraction(1, 1000), "l"),
                ),
                # Spoons
                Unit(
                    ("tsp", "tsps", "teaspoons", "teaspoon", "tea spoon", "tea spoons"),
                    Definition(Fraction(5, 1000), "l"),
                ),
                Unit(
                    (
                        "tbsp",
                        "tbsps",
                        "tablespoon",
                        "tablespoons",
                        "table spoon",
                        "table spoons",
                    ),
                    Definition(Fraction(15, 1000), "l"),
                ),
                # Crazy
                Unit(("cup", "cups"), Definition(236.58824, "ml")),
                Unit(("pint", "pints"), Definition(568.261, "ml")),
            ]
        ),
        # Other non-specific units
        "clove": RelatedUnitSet([Unit(("clove", "cloves"))]),
        "bulb": RelatedUnitSet([Unit(("bulb", "bulbs"))]),
        "can": RelatedUnitSet([Unit(("can", "cans", "tin", "tins"))]),
        "pinch": RelatedUnitSet([Unit(("pinch", "pinches"))]),
        "knob": RelatedUnitSet([Unit(("knob", "knobs"))]),
        "packet": RelatedUnitSet([Unit(("packet", "packets", "pack", "packs"))]),
        "box": RelatedUnitSet([Unit(("box", "boxes", "boxen"))]),
        "bag": RelatedUnitSet([Unit(("bag", "bags"))]),
        "sack": RelatedUnitSet([Unit(("sack", "sacks"))]),
        "sachet": RelatedUnitSet([Unit(("sachet", "sachets"))]),
        "rasher": RelatedUnitSet([Unit(("rasher", "rashers"))]),
        "strip": RelatedUnitSet([Unit(("strip", "strips"))]),
    }
)
"""
The units known to this system.
"""


ALL_UNITS_REGEX_LITERAL = "|".join(
    re.escape(name).replace(r"\ ", r"\s+") for name in UNIT_SYSTEM.iter_names()
)
"""
A regex literal which matches any of the unit names defined above.
"""
