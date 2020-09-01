import pytest

import re

from recipe_grid.units import (
    Unit,
    UNITS,
    ALL_UNITS_REGEX_LITERAL,
)


def test_no_duplicate_names() -> None:
    names = set()
    for related_unit_set in UNITS.values():
        for unit in related_unit_set.units:
            for name in unit.names:
                assert name not in names
                names.add(name)


@pytest.mark.parametrize("kind", UNITS)
def test_one_base_unit_per_set(kind: str) -> None:
    related_unit_set = UNITS[kind]
    base_units = [unit for unit in related_unit_set.units if unit.definition is None]
    assert len(base_units) == 1


@pytest.mark.parametrize("kind", UNITS)
def test_units_are_well_defined(kind: str) -> None:
    related_unit_set = UNITS[kind]

    name_to_unit = {
        name: unit for unit in related_unit_set.units for name in unit.names
    }

    for unit in related_unit_set.units:
        visited = [unit]

        def visit_definition_of(unit: Unit) -> None:
            if unit.definition is None:
                return
            elif unit.definition.unit not in name_to_unit:
                assert False, (
                    f"Unit {unit.name} is defined in terms of "
                    f"undefined unit {unit.definition.unit}."
                )
            else:
                parent_unit = name_to_unit[unit.definition.unit]
                if parent_unit in visited:
                    assert False, f"Dependency cycle found involving {parent_unit.name}"
                visited.append(parent_unit)
                visit_definition_of(parent_unit)

        visit_definition_of(unit)


def test_all_units_regex_literal() -> None:
    regex = re.compile(ALL_UNITS_REGEX_LITERAL)
    for unit_set in UNITS.values():
        for unit in unit_set.units:
            for name in unit.names:
                assert regex.match(name) is not None
