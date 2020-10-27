r"""
The following output-agnostic data structure is used to represent a recipe in
tabular form.

The basic data structure consists of a :py:class:`Table` object which contains
a set of nested lists containing a 2D array of :py:class:`Cell` and
:py:class:`ExtendedCell` objects. Each entry in the array represents a cell in
the table.

Where a cell spans multiple rows or columns, the top-left cell is defined with
a :py:class:`Cell` instance (with :py:attr:`Cell.rows` and
:py:attr:`Cell.columns` set appropriately) and the occluded cells are filled
with :py:class:`ExtendedCell` instances. For convenience, the
:py:meth:`Table.from_dict` class method is provided which can automatically fill
in :py:class:`ExtendedCell` instances when only :py:class`Cell`\ s are given.

.. autoclass:: Table
    :members:

.. autoclass:: Cell
    :members:
    :undoc-members:

.. autoclass:: ExtendedCell
    :members:
    :undoc-members:

Cells have four borders whose display styles are dictated by the ``border_*``
attributes of the :py:class:`Cell`. The border styles are:

.. autoclass:: BorderType
    :members:
"""

from typing import (
    List,
    Sequence,
    MutableMapping,
    Mapping,
    Tuple,
    Set,
    Optional,
    Union,
    Iterable,
    Iterator,
    Generic,
    TypeVar,
    cast,
)

from dataclasses import dataclass, replace

from enum import Enum, auto


T = TypeVar("T")


class BorderType(Enum):
    none = auto()
    """
    No border. Used only for cells which are to be rendered 'outside' the
    table.
    """

    normal = auto()
    """
    A normal border style which will surround most cells.
    """

    sub_recipe = auto()
    """
    A border drawn round a sub recipe; typically thicker than the normal border
    style.
    """


@dataclass
class Cell(Generic[T]):
    value: T
    """The value contained in this cell."""

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
class ExtendedCell(Generic[T]):
    """
    Represents parts of a table which are filled not with a new cell but with
    the extension of an adjacent cell. (Used as a 'dummy' value in
    :py:class:`Table`.)
    """

    cell: Cell[T]
    """A reference to the cell which occludes this cell."""

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
class Table(Generic[T]):
    cells: Sequence[Sequence[Union[Cell[T], ExtendedCell[T]]]]
    """
    The table cells. A dense 2D array indexed as ``cells[row][column]`` with
    spaces covered by extended cells being denoted using
    :py:class:`ExtendedCell`.
    """

    @classmethod
    def from_dict(cls, table_dict: Mapping[Tuple[int, int], Cell[T]]) -> "Table[T]":
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
        cells: List[List[Optional[Union[Cell[T], ExtendedCell[T]]]]] = [
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

        return cls(cast(Sequence[Sequence[Union[Cell[T], ExtendedCell[T]]]], cells))

    def to_dict(self) -> Mapping[Tuple[int, int], Cell[T]]:
        r"""
        Return a dictionary mapping from (row, column) to :py:class:`Cell`
        (omitting :py:class:`ExtendedCell`\ s).
        """
        return {
            (row, column): cell
            for (row, column), cell in self
            if isinstance(cell, Cell)
        }

    @property
    def columns(self) -> int:
        """Number of columns in this table"""
        return len(self.cells[0])

    @property
    def rows(self) -> int:
        """Number of rows in this table"""
        return len(self.cells)

    def __iter__(
        self,
    ) -> Iterator[Tuple[Tuple[int, int], Union[Cell[T], ExtendedCell[T]]]]:
        """
        Iterate over ((row, column), cell_or_extended_cell) tuples in raster
        scan order.
        """
        for row, row_cells in enumerate(self.cells):
            for column, cell in enumerate(row_cells):
                yield (row, column), cell

    def __getitem__(self, index: Tuple[int, int]) -> Union[Cell[T], ExtendedCell[T]]:
        """Get the entry at the specified row and column."""
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


def combine_tables(tables: Iterable[Table[T]], axis: int) -> Table[T]:
    """
    Combine two or more tables by sacking them vertically (axis=0) or
    horizontally (axis=1).
    """
    out: MutableMapping[Tuple[int, int], Cell[T]] = {}

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


def right_pad_table(table: Table[T], columns: int) -> Table[T]:
    """
    Expand the provided table to ensure it has at least ``columns`` columns
    wide, extending the width of the right-most cells in each row to make up
    the width.
    """
    if table.columns >= columns:
        return table
    else:
        rightmost_cell_coordinates: Set[Tuple[int, int]] = set()
        for row in range(table.rows):
            last_column = table[row, -1]
            if isinstance(last_column, Cell):
                rightmost_cell_coordinates.add((row, table.columns - 1))
            else:
                rightmost_cell_coordinates.add(
                    (row - last_column.drow, table.columns - last_column.dcolumn - 1)
                )

        return Table.from_dict(
            {
                (row, column): (
                    cell
                    if (row, column) not in rightmost_cell_coordinates
                    else replace(cell, columns=columns - column)
                )
                for (row, column), cell in table.to_dict().items()
            }
        )


def set_border_around_table(table: Table[T], border_type: BorderType) -> Table[T]:
    """
    Return a copy of the provided table with the border style changed around
    all outside cell edges.
    """

    def to_cell_coord(row: int, column: int) -> Tuple[int, int]:
        cell_or_extended_cell = table[row, column]
        if isinstance(cell_or_extended_cell, Cell):
            return (row, column)
        else:
            return (
                row - cell_or_extended_cell.drow,
                column - cell_or_extended_cell.dcolumn,
            )

    left_edge_cells = set(to_cell_coord(row, 0) for row in range(table.rows))
    right_edge_cells = set(
        to_cell_coord(row, table.columns - 1) for row in range(table.rows)
    )
    top_edge_cells = set(to_cell_coord(0, column) for column in range(table.columns))
    bottom_edge_cells = set(
        to_cell_coord(table.rows - 1, column) for column in range(table.columns)
    )

    def cell_with_new_border(row: int, column: int) -> Cell[T]:
        cell = cast(Cell[T], table[row, column])

        changes: MutableMapping[str, BorderType] = {}
        if (row, column) in left_edge_cells:
            changes["border_left"] = border_type
        if (row, column) in right_edge_cells:
            changes["border_right"] = border_type
        if (row, column) in top_edge_cells:
            changes["border_top"] = border_type
        if (row, column) in bottom_edge_cells:
            changes["border_bottom"] = border_type

        if changes:
            return replace(cell, **changes)
        else:
            return cell

    return Table.from_dict(
        {
            (row, column): cell_with_new_border(row, column)
            for (row, column), cell in table
            if isinstance(cell, Cell)
        }
    )
