import pytest

from typing import List, Union

from recipe_grid.renderer.table import (
    EmptyTableError,
    CellExpectedError,
    ExtendedCellExpectedError,
    ExtendedCellReferenceError,
    ExtendedCellCoordinateError,
    MissingCellError,
    Table,
    Cell,
    ExtendedCell,
    combine_tables,
    right_pad_table,
)


class TestTable:
    def test_indexing(self) -> None:
        # Minimal case
        c00 = Cell("0,0")
        t = Table([[c00]])
        assert t[0, 0] == c00
        assert t.rows == 1
        assert t.columns == 1

        # Plain cells only
        c01 = Cell("0,1")
        c10 = Cell("1,0")
        c11 = Cell("1,1")
        t = Table([[c00, c01], [c10, c11]])
        assert t[0, 0] == c00
        assert t[0, 1] == c01
        assert t[1, 0] == c10
        assert t[1, 1] == c11
        assert t.rows == 2
        assert t.columns == 2

        # With extended cells
        c0x = Cell("1,x", 1, 2)
        t = Table([[c0x, ExtendedCell(c0x, 0, 1)], [c10, c11]])
        assert t[0, 0] == c0x
        assert t[0, 1] == ExtendedCell(c0x, 0, 1)
        assert t[1, 0] == c10
        assert t[1, 1] == c11
        assert t.rows == 2
        assert t.columns == 2

        # With asymmetry
        c0x = Cell("1,x", 1, 2)
        t = Table([[c0x, ExtendedCell(c0x, 0, 1)]])
        assert t[0, 0] == c0x
        assert t[0, 1] == ExtendedCell(c0x, 0, 1)
        assert t.rows == 1
        assert t.columns == 2

    def test_validation_empty_table(self) -> None:
        with pytest.raises(EmptyTableError):
            Table([])
        with pytest.raises(EmptyTableError):
            Table([[]])

    def test_validation_extended_cell_in_wrong_place(self) -> None:
        # Top left corner
        with pytest.raises(CellExpectedError):
            Table([[ExtendedCell(Cell(123), 0, 0)]])
        # Elsewhere
        description: List[List[Union[Cell[int], ExtendedCell[int]]]] = [
            [Cell(123), ExtendedCell(Cell(123), 0, 1)]
        ]
        with pytest.raises(CellExpectedError):
            Table(description)

    @pytest.mark.parametrize("rows, columns", [(1, 2), (2, 1), (2, 2)])
    def test_validation_extended_cell_is_cell(self, rows: int, columns: int) -> None:
        with pytest.raises(ExtendedCellExpectedError):
            Table([[Cell(123, rows, columns), Cell(123)], [Cell(123), Cell(123)]])

    @pytest.mark.parametrize("rows, columns", [(1, 2), (2, 1), (2, 2)])
    def test_validation_extended_cell_is_missing(self, rows: int, columns: int) -> None:
        with pytest.raises(MissingCellError):
            Table([[Cell(123, rows, columns)]])

    def test_validation_extended_cell_bad_reference(self) -> None:
        description: List[List[Union[Cell[int], ExtendedCell[int]]]] = [
            [Cell(123, columns=2), ExtendedCell(Cell(123), 0, 1)]
        ]
        with pytest.raises(ExtendedCellReferenceError):
            Table(description)

    def test_validation_extended_cell_bad_coordinate(self) -> None:
        cell = Cell(123, 1, 2)
        description: List[List[Union[Cell[int], ExtendedCell[int]]]]

        description = [[cell, ExtendedCell(cell, 1, 1)]]
        with pytest.raises(ExtendedCellCoordinateError):
            Table(description)

        description = [[cell, ExtendedCell(cell, 0, 0)]]
        with pytest.raises(ExtendedCellCoordinateError):
            Table(description)

    def test_validation_ragged_rows(self) -> None:
        with pytest.raises(MissingCellError):
            Table([[Cell(123)], [Cell(123), Cell(123)]])
        with pytest.raises(MissingCellError):
            Table([[Cell(123), Cell(123)], [Cell(123)]])

    def test_from_dict(self) -> None:
        # Minimal case
        c00 = Cell("0,0")
        assert Table.from_dict({(0, 0): c00}) == Table([[c00]])

        # Plain cells only
        c01 = Cell("0,1")
        c10 = Cell("1,0")
        c11 = Cell("1,1")
        assert Table.from_dict(
            {(0, 0): c00, (0, 1): c01, (1, 0): c10, (1, 1): c11}
        ) == Table([[c00, c01], [c10, c11]])

        # With Simple extended cell
        cxx = Cell("0,x", 2, 3)
        description: List[List[Union[Cell[str], ExtendedCell[str]]]] = [
            [cxx, ExtendedCell(cxx, 0, 1), ExtendedCell(cxx, 0, 2)],
            [
                ExtendedCell(cxx, 1, 0),
                ExtendedCell(cxx, 1, 1),
                ExtendedCell(cxx, 1, 2),
            ],
        ]
        assert Table.from_dict({(0, 0): cxx}) == Table(description)

        # With normal and extended cells
        c0x = Cell("0,x", 1, 2)
        description = [[c0x, ExtendedCell(c0x, 0, 1)], [c10, c11]]
        assert Table.from_dict({(0, 0): c0x, (1, 0): c10, (1, 1): c11}) == Table(
            description
        )

    def test_from_dict_validation_empty(self) -> None:
        with pytest.raises(EmptyTableError):
            Table.from_dict({})

    @pytest.mark.parametrize("row, column", [(2, 0), (0, 2), (2, 2)])
    def test_from_dict_validation_missing_cells(self, row: int, column: int) -> None:
        with pytest.raises(MissingCellError):
            Table.from_dict({(0, 0): Cell(123), (row, column): Cell(123)})

    def test_to_dict(self) -> None:
        c10 = Cell("1,0")
        c11 = Cell("1,1")
        c0x = Cell("0,x", 1, 2)
        d = {
            (0, 0): c0x,
            (1, 0): c10,
            (1, 1): c11,
        }
        assert Table.from_dict(d).to_dict() == d


class TestCombineTables:
    def test_no_tables(self) -> None:
        with pytest.raises(EmptyTableError):
            combine_tables([], axis=0)

    def test_single_table(self) -> None:
        orig = Table.from_dict({(0, 0): Cell(123, columns=2)})
        assert combine_tables([orig], axis=0) == orig
        assert combine_tables([orig], axis=1) == orig

    def test_multiple_tables(self) -> None:
        t1 = Table.from_dict({(0, 0): Cell(123, columns=2)})
        t2 = Table.from_dict({(0, 0): Cell(123), (0, 1): Cell(123)})
        assert combine_tables([t1, t2], axis=0) == Table.from_dict(
            {(0, 0): Cell(123, columns=2), (1, 0): Cell(123), (1, 1): Cell(123)}
        )

        t3 = Table.from_dict({(0, 0): Cell(123, rows=2)})
        t4 = Table.from_dict({(0, 0): Cell(123), (1, 0): Cell(123)})
        assert combine_tables([t3, t4], axis=1) == Table.from_dict(
            {(0, 0): Cell(123, rows=2), (0, 1): Cell(123), (1, 1): Cell(123)}
        )

    def test_mismatched_shapes(self) -> None:
        with pytest.raises(MissingCellError):
            combine_tables(
                [
                    Table.from_dict({(0, 0): Cell(123, columns=2)}),
                    Table.from_dict({(0, 0): Cell(123)}),
                ],
                axis=0,
            )

        with pytest.raises(MissingCellError):
            combine_tables(
                [
                    Table.from_dict({(0, 0): Cell(123, rows=2)}),
                    Table.from_dict({(0, 0): Cell(123)}),
                ],
                axis=1,
            )


class TestRightPadTable:
    def test_already_wide_enough(self) -> None:
        # Two cells
        t1 = Table([[Cell(123), Cell(123)]])
        assert right_pad_table(t1, 2) == t1

        # A wide cell
        t2 = Table.from_dict({(0, 0): Cell(123, columns=2)})
        assert right_pad_table(t2, 2) == t2

        # Wider than needed
        t3 = Table.from_dict({(0, 0): Cell(123, columns=3)})
        assert right_pad_table(t3, 2) == t3

    def test_expand_single_cell(self) -> None:
        t1 = Table.from_dict({(0, 0): Cell(123)})
        assert right_pad_table(t1, 2) == Table.from_dict({(0, 0): Cell(123, columns=2)})

        t2 = Table.from_dict({(0, 0): Cell(123, columns=2)})
        assert right_pad_table(t2, 4) == Table.from_dict({(0, 0): Cell(123, columns=4)})

    def test_expand_multiple_cells_including_rows_with_only_extended_cells(
        self,
    ) -> None:
        t1 = Table.from_dict(
            {
                (0, 0): Cell(123, columns=2, rows=2),
                (2, 0): Cell(123),
                (2, 1): Cell(123),
            }
        )
        assert right_pad_table(t1, 4) == Table.from_dict(
            {
                (0, 0): Cell(123, columns=4, rows=2),
                (2, 0): Cell(123),
                (2, 1): Cell(123, columns=3),
            }
        )
