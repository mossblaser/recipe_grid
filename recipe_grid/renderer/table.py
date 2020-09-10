"""
An data structure for describing tables generated from
:py:mod:`recipe_grid.recipe` descriptions. (Another) intermediate
representation prior to rendering.
"""

from typing import (
    List,
    MutableMapping,
    Mapping,
    Tuple,
    Optional,
    Union,
    Iterable,
    Iterator,
    cast,
)

from dataclasses import dataclass

from enum import Enum, auto

from recipe_grid.recipe import RecipeTreeNode


class BorderType(Enum):
    none = auto()
    normal = auto()
    sub_recipe = auto()


@dataclass
class Cell:
    node: RecipeTreeNode
    """
    The recipe node to be shown in this cell.

    Firstly, the obvious cases:

    * :py:class:`~ingredient` is shown as is.
    * :py:class:`~Reference` is shown as its label.
    * :py:class:`~Step` is shown as its description.

    Finally, :py:class:`~SubRecipe`. These may appear in the table for one of
    two purposes:

    * For single-output sub recipes they should be rendered as a header row
      above the sub recipe cells containing the output name as text.
    * For multiple-output sub-recipes they should be placed in a cell to the
      right of the sub-recipe and contain (vertically arranged) all of the
      output names for the sub recipe.
    """

    rows: int = 1
    columns: int = 1
    """
    The number of columns (to the right) or rows (below) over which this cell
    extends.
    """

    border_left: BorderType = BorderType.normal
    border_right: BorderType = BorderType.normal
    border_top: BorderType = BorderType.normal
    border_bottom: BorderType = BorderType.normal
    """
    The border styles for this cell.
    """


@dataclass
class ExtendedCell:
    """
    Represents parts of a table which are filled not with a new cell but with
    the extension of an adjacent cell. (Used as a 'dummy' value in
    :py:class:`Table`.)
    """

    cell: Cell

    drow: int
    dcolumn: int
    """
    The delta in coordinate from the cell this :py:class:`ExtendedCell`
    resides.
    """


class InconsistentTableLayoutError(ValueError):
    """
    Base class for exceptions thrown when a badly formatted table is provided.
    """


class EmptyTableError(InconsistentTableLayoutError):
    """Thrown when an empty table is given."""


class CellExpectedError(InconsistentTableLayoutError):
    """Thrown when an :py:class:`ExtendedCell` is found when a :py:class:`Cell` was expected."""


class ExtendedCellExpectedError(InconsistentTableLayoutError):
    """Thrown when a :py:class:`Cell` was found and a :py:class:`ExtendedCell` was expected."""


class ExtendedCellReferenceError(InconsistentTableLayoutError):
    """Thrown when an :py:class:`ExtendedCell` has a reference to the wrong cell in it."""


class ExtendedCellCoordinateError(InconsistentTableLayoutError):
    """Thrown when an :py:class:`ExtendedCell` has the wrong coordinates in it."""


class MissingCellError(InconsistentTableLayoutError):
    """Thrown when a missing cell is encountered."""


@dataclass
class Table:
    cells: List[List[Union[Cell, ExtendedCell]]]
    """
    The table cells. A dense 2D array indexed as ``cells[row][column]`` with
    spaces covered by extended cells being denoted using
    :py:class:`ExtendedCell`.
    """

    @classmethod
    def from_dict(cls, table_dict: Mapping[Tuple[int, int], Cell]) -> "Table":
        """
        Construct a :py:class:`Table` from a dictionary mapping (row, column)
        to :py:class:`Cell`.
        """
        # Compute table dimensions
        try:
            rows = max(row + cell.rows for (row, _column), cell in table_dict.items())
            columns = max(
                column + cell.columns for (_row, column), cell in table_dict.items()
            )
        except ValueError:  # Thrown when max is provided an empty list
            raise EmptyTableError()

        # Populate the table
        cells: List[List[Optional[Union[Cell, ExtendedCell]]]] = [
            [None for _ in range(columns)] for _ in range(rows)
        ]
        for (row, column), cell in table_dict.items():
            cells[row][column] = cell

            for drow in range(cell.rows):
                for dcolumn in range(cell.columns):
                    if drow != 0 or dcolumn != 0:
                        cells[row + drow][column + dcolumn] = ExtendedCell(
                            cell, drow, dcolumn
                        )

        # Check for missing cells
        for row, row_cells in enumerate(cells):
            for column, maybe_cell in enumerate(row_cells):
                if maybe_cell is None:
                    raise MissingCellError(row, column)

        return cls(cast(List[List[Union[Cell, ExtendedCell]]], cells))

    def to_dict(self) -> Mapping[Tuple[int, int], Cell]:
        return {
            (row, column): cell
            for (row, column), cell in self
            if isinstance(cell, Cell)
        }

    @property
    def columns(self) -> int:
        return len(self.cells[0])

    @property
    def rows(self) -> int:
        return len(self.cells)

    def __iter__(self) -> Iterator[Tuple[Tuple[int, int], Union[Cell, ExtendedCell]]]:
        for row, row_cells in enumerate(self.cells):
            for column, cell in enumerate(row_cells):
                yield (row, column), cell

    def __getitem__(self, index: Tuple[int, int]) -> Union[Cell, ExtendedCell]:
        row, column = index
        return self.cells[row][column]

    def __post_init__(self) -> None:
        if len(self.cells) == 0 or len(self.cells[0]) == 0:
            raise EmptyTableError()

        # Verify that the table description is consistent.
        to_check = [
            (row, column) for row in range(self.rows) for column in range(self.columns)
        ]
        present = [(row, column) for (row, column), _cell in self]
        if present != to_check:
            row, column = min(
                (set(to_check) | set(present)) - set(to_check).intersection(present)
            )
            raise MissingCellError(row, column)

        while to_check:
            row, column = to_check.pop(0)

            try:
                cell = self[row, column]
            except IndexError:
                raise MissingCellError(row, column)

            if not isinstance(cell, Cell):
                raise CellExpectedError(cell, row, column)

            # Check that all extended cell objects are consistent
            if cell.columns != 1 or cell.rows != 1:
                for erow in range(row, row + cell.rows):
                    for ecolumn in range(column, column + cell.columns):
                        if erow != row or ecolumn != column:
                            try:
                                extended_cell = self[erow, ecolumn]
                            except IndexError:
                                raise MissingCellError(erow, ecolumn)

                            if not isinstance(extended_cell, ExtendedCell):
                                raise ExtendedCellExpectedError(
                                    extended_cell, erow, ecolumn
                                )

                            if extended_cell.cell != cell:
                                raise ExtendedCellReferenceError(
                                    extended_cell, erow, ecolumn
                                )

                            if (
                                extended_cell.drow != erow - row
                                or extended_cell.dcolumn != ecolumn - column
                            ):
                                raise ExtendedCellCoordinateError(
                                    extended_cell, erow, ecolumn
                                )

                            to_check.remove((erow, ecolumn))


def combine_tables(tables: Iterable[Table], axis: int) -> Table:
    """
    Combine two or more tables by sacking them vertically (axis=0) or
    horizontally (axis=1).
    """
    out: MutableMapping[Tuple[int, int], Cell] = {}

    row_offset = 0
    column_offset = 0
    for table in tables:
        for (row, column), cell in table.to_dict().items():
            out[row + row_offset, column + column_offset] = cell

        if axis == 0:
            row_offset += table.rows
        elif axis == 1:
            column_offset += table.columns

    return Table.from_dict(out)
