import pytest

from typing import Union

from fractions import Fraction

from recipe_grid.number_parser import number


class TestNumber:
    @pytest.mark.parametrize(
        "value, exp",
        [
            # Integers
            ("0", 0),
            ("123", 123),
            # Floats
            ("0.", 0.0),
            ("16.25", 16.25),
            # Fractions
            ("1/2", Fraction(1, 2)),
            ("1 2/3", Fraction(5, 3)),
            ("10 20/30", Fraction(32, 3)),
            # Fractions with spaces
            ("1   2 / 3", Fraction(5, 3)),
        ],
    )
    def test_valid(self, value: str, exp: Union[int, float, Fraction]) -> None:
        n = number(value)
        assert n == exp
        assert type(n) is type(exp)

    @pytest.mark.parametrize(
        "value",
        [
            # Empty
            "",
            # Invalid float
            "1.2.3",
            # Invalid fraction
            "1/",
            "/1",
            "1/2/3",
        ],
    )
    def test_invalid(self, value: str) -> None:
        with pytest.raises(ValueError):
            number(value)
