"""
A string type in which embedded numerical values can be re-scaled.

.. autoclass:: ScaledValueString

"""

from typing import Union, Callable, List, Sequence, Tuple, Any

from collections.abc import Iterable

from fractions import Fraction

from recipe_grid.number_formatting import format_number

Number = Union[int, float, Fraction]


__all__ = ["ScaledValueString"]


class ScaledValueString:
    """
    A string which contains some numerical values which may be re-scaled by a
    fixed factor.

    This type is very specifically aimed at strings within recipes of the style
    "divide into 8 burgers about 10cm in diameter". Here when the recipe is
    scaled up or down, the '8' should be scaled but the '10' should not. Here a
    :py:class:`ScaledValueString` would be defined like so:

        >>> for_8_burgers = ScaledValueString(
        ...     ["divide into ", 8, " burgers about 10cm in diameter"]
        ... )

    This could be scaled up like so:

        >>> for_16_burgers = for_8_burgers.scale(2)
        >>> for_16_burgers.render()
        'divide into 16 burgers about 10cm in diameter'
    """

    _string: Tuple[Union[str, Number], ...]

    def __init__(
        self, string: Union[str, Number, Sequence[Union[str, Number]]] = ""
    ) -> None:
        if not isinstance(string, Iterable):
            string = [string]

        # Normalise string by combining adjacent strings
        normalised_string: List[Union[str, Number]] = []
        for part in string:
            if (
                isinstance(part, str)
                and normalised_string
                and isinstance(normalised_string[-1], str)
            ):
                normalised_string[-1] += part
            else:
                normalised_string.append(part)

        self._string = tuple(part for part in normalised_string if part != "")

    def render(
        self,
        format_number: Callable[[Number], str] = format_number,
        format_string: Callable[[str], str] = str,
    ) -> str:
        return "".join(
            format_string(part) if isinstance(part, str) else format_number(part)
            for part in self._string
        )

    def __str__(self) -> str:
        return self.render()

    def __repr__(self) -> str:
        return "{}({!r})".format(
            type(self).__name__,
            (self._string[0] if len(self._string) == 1 else self._string),
        )

    def __add__(
        self, other: Union[str, Number, "ScaledValueString"]
    ) -> "ScaledValueString":
        if not isinstance(other, ScaledValueString):
            other = ScaledValueString(other)
        return ScaledValueString(self._string + other._string)

    def scale(self, multiplier: Number) -> "ScaledValueString":
        return ScaledValueString(
            [
                part if isinstance(part, str) else part * multiplier
                for part in self._string
            ]
        )

    def __hash__(self) -> int:
        return hash(self._string)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, ScaledValueString) and self._string == other._string

    def lower(self) -> "ScaledValueString":
        return ScaledValueString(
            [part.lower() if isinstance(part, str) else part for part in self._string]
        )

    def upper(self) -> "ScaledValueString":
        return ScaledValueString(
            [part.upper() if isinstance(part, str) else part for part in self._string]
        )

    def lstrip(self) -> "ScaledValueString":
        return ScaledValueString(
            [
                part.lstrip() if isinstance(part, str) and i == 0 else part
                for i, part in enumerate(self._string)
            ]
        )

    def rstrip(self) -> "ScaledValueString":
        return ScaledValueString(
            [
                part.rstrip()
                if isinstance(part, str) and i == len(self._string) - 1
                else part
                for i, part in enumerate(self._string)
            ]
        )

    def strip(self) -> "ScaledValueString":
        return self.lstrip().rstrip()
