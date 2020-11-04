"""
Abstract Syntax Tree (AST) for the recipe syntax.
"""

from dataclasses import dataclass, field

from fractions import Fraction
from typing import cast, Any, List, Optional, Union, Mapping, Tuple

import peggie

# XXX: Work-around for MyPy issue python/mypy#3186 whereby int and friends are
# not a subtype of numbers.Number.
Number = Union[int, float, Fraction]


@dataclass
class AST:
    """
    Base class for all AST nodes.
    """

    offset: int = field(compare=False)
    """Source offset (in chars) of the corresponding part of the recipe."""


@dataclass
class Recipe(AST):
    """
    Root for all recipe ASTs.
    """

    offset: int = field(init=False, repr=False, compare=False)

    stmts: List["Stmt"]
    """
    A list of :py:class:`Stmt` objects corresponding with the statements in the
    original recipe.
    """

    def __post_init__(self) -> None:
        self.offset = self.stmts[0].offset


@dataclass
class Stmt(AST):
    offset: int = field(init=False, repr=False, compare=False)

    expr: "Expr"
    """The :py:class:`Expr` contained in this statement."""

    outputs: Optional[List["String"]] = None
    """A list of explicitly named outputs produced by this statement."""

    named: bool = False
    """
    True if ``:=`` was used (indicating that this sub-recipe should be
    explicitly named in the displayed output), False otherwise.
    """

    def __post_init__(self) -> None:
        if self.outputs:
            self.offset = self.outputs[0].offset
        else:
            self.offset = self.expr.offset


@dataclass
class Expr(AST):
    """Base class for expression AST nodes."""

    pass


@dataclass
class Step(Expr):
    """A step, e.g. 'mix(tomatoes, herbs)'."""

    offset: int = field(init=False, repr=False, compare=False)

    name: "String"
    """The description of the step ('mix' in this example)."""

    inputs: List["Expr"]
    """The list of inputs to this step, ('tomatoes' and 'herbs' in this example)."""

    def __post_init__(self) -> None:
        self.offset = self.name.offset


@dataclass
class Reference(Expr):
    """A reference to an ingredient or a sub-recipe."""

    offset: int = field(init=False, repr=False, compare=False)

    name: "String"
    """The name of the ingredient or sub-recipe to be used."""

    quantity_or_proportion: Optional[Union["Quantity", "Proportion"]] = None
    """
    The quantity (e.g. '300g') or proportion (e.g. '1/2 *') of the referenced
    ingredient to be included. None if no quantity is specified.
    """

    def __post_init__(self) -> None:
        if self.quantity_or_proportion is not None:
            self.offset = self.quantity_or_proportion.offset
        else:
            self.offset = self.name.offset


@dataclass
class Quantity(AST):
    """An absolute quantity."""

    value: Number
    """
    The scalar quantity. Either a float, or where the amount was given as a
    fraction, a :py:class:`~Fraction`.
    """

    unit: Optional["String"]
    """The name of the unit, or None if a unitless quantity."""

    value_unit_spacing: str
    """The whitespace, if any, used between the value and the unit."""

    preposition: str
    """
    Where a quantity is followed by an unquoted preposition (e.g. the 'of' in
    '50g of butter' or '{1 sack} of pizza'), a string containing that
    preposition. Otherwise an empty string
    """


@dataclass
class Proportion(AST):
    """A relative proportion of a quantity."""

    value: Optional[Number]
    """
    The proportion. A number between 0.0 and 1.0 giving the proportion
    indicated, or None indicating 'rest of'.
    """

    percentage: bool
    """True if the amount was specified as a percentage."""

    remainder_wording: Optional[str]
    """
    When value is None, the string to used to mean 'remainder' (e.g. 'rest' in
    'rest of sauce').
    """

    preposition: str
    """
    The words and whitespace following a value or remainder. Examples:

    * "rest of the spam" -> " of the"
    * "1/3 of sauce" -> " of"
    * "10% spam" -> "%"
    * "0.5 * spam" -> " *"
    """


@dataclass
class String(AST):
    """
    A string which may contain numerical values which will be interpolated as
    the recipe is re-scaled.
    """

    def __init__(
        self,
        value: Union[
            str,
            Tuple[int, str],
            List[Union["Substring", "InterpolatedValue"]],
        ],
    ) -> None:
        if isinstance(value, str):
            self.substrings = [Substring(0, value)]
        elif isinstance(value, tuple):
            self.substrings = [Substring(*value)]
        else:
            self.substrings = value

        self.offset = self.substrings[0].offset

    offset: int = field(init=False, repr=False, compare=False)

    substrings: List[Union["Substring", "InterpolatedValue"]]
    """The components which, when concatenated,  make up the string."""


@dataclass
class Substring(AST):
    """A substring which should be used literally."""

    string: str


@dataclass
class InterpolatedValue(AST):
    """
    A number, which forms part of a string, which should be scaled with the
    recipe.
    """

    number: Number


ESCAPE_CHARS: Mapping[str, str] = {
    "\\": "\\",
    "'": "'",
    '"': '"',
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
}
"""
An enumeration of all valid escape sequences. All others will be passed through
as a backslash followed by the escaped character.
"""


class RecipeTransformer(peggie.ParseTreeTransformer):
    """
    Transformer which transforms a raw :py:mod:`peggie` parse tree into a more
    friendly :py:class:`AST`.
    """

    def _transform_regex(self, regex: peggie.Regex) -> peggie.Regex:
        return regex

    def decimal(
        self, _pt: peggie.ParseTree, children: Any
    ) -> Tuple[int, Union[int, float]]:
        number = float(children.string)
        if "." not in children.string:
            return children.start, int(number)
        else:
            return children.start, number

    def fraction(self, _pt: peggie.ParseTree, children: Any) -> Tuple[int, Fraction]:
        maybe_integer, numer, _sp1, _slash, _sp2, denom = children
        fraction = Fraction(int(numer.string), int(denom.string))

        offset = numer.start
        integer = 0

        if maybe_integer is not None:
            integer_re, _sp = maybe_integer
            offset = integer_re.start
            integer = int(integer_re.string)

        return offset, integer + fraction

    def naked_string(self, _pt: peggie.ParseTree, children: Any) -> List[Substring]:
        return [Substring(children.start, children.string)]

    def quoted_string(self, _pt: peggie.ParseTree, children: Any) -> List[Substring]:
        q1, body, _q2 = children

        string = "".join(
            char.string
            if isinstance(char, peggie.Regex)
            else ESCAPE_CHARS.get(char[1].string, char[1].string)
            for char in body
        )

        return [Substring(q1.start, string)]

    d_quoted_string = quoted_string
    s_quoted_string = quoted_string

    def bracketed_string(
        self, pt: peggie.ParseTree, children: Any
    ) -> List[Union[Substring, InterpolatedValue]]:
        b1, body, _b2 = children

        out: List[Union[Substring, InterpolatedValue]] = []

        current_string_segment = ""
        current_string_segment_offset = b1.start

        for char in body:
            if isinstance(char, tuple):
                offset, number = char

                if current_string_segment:
                    out.append(
                        Substring(
                            current_string_segment_offset,
                            current_string_segment,
                        )
                    )
                current_string_segment = ""
                current_string_segment_offset = None

                out.append(InterpolatedValue(offset, number))
            else:
                if isinstance(char, peggie.Regex):
                    offset = char.start
                    char = char.string
                else:
                    backslash, char = char
                    offset = backslash.start
                    char = ESCAPE_CHARS.get(char.string, char.string)
                current_string_segment += char
                if current_string_segment_offset is None:
                    current_string_segment_offset = offset

        if current_string_segment_offset is not None:
            out.append(
                Substring(
                    current_string_segment_offset,
                    current_string_segment,
                )
            )

        return out

    def string(self, _pt: peggie.ParseTree, children: Any) -> String:
        first, rest = children

        out = String(first)
        if rest is not None:
            sp, rest_text = rest
            if sp is not None:
                out.substrings.append(Substring(sp.start, sp.string))
            out.substrings.extend(rest_text.substrings)

        return out

    static_string = string

    def known_unit(self, _pt: peggie.ParseTree, children: Any) -> String:
        return String([Substring(children.start, children.string)])

    def proportion(self, pt: peggie.Alt, children: Any) -> Proportion:
        if pt.choice_index == 0:  # Remainder
            remainder, maybe_preposition = children

            preposition = ""
            if maybe_preposition is not None:
                preposition_sp, preposition_word = maybe_preposition
                preposition = preposition_sp.string + preposition_word.string

            return Proportion(
                remainder.start, None, False, remainder.string, preposition
            )
        else:  # Number
            (offset, number), some_preposition = children

            percentage = False
            preposition = ""

            preposition_choice = cast(
                peggie.Alt, cast(peggie.Concat, pt.value).values[1]
            ).choice_index
            if preposition_choice == 0:  # e.g. " of the"
                preposition_sp, preposition_word = some_preposition
                preposition = preposition_sp.string + preposition_word.string
            elif preposition_choice == 1:  # e.g. "% of the" or "%"
                percentage = True
                maybe_sp, perc, maybe_preposition = some_preposition
                if maybe_sp is not None:
                    preposition = maybe_sp.string
                preposition += perc.string
                if maybe_preposition is not None:
                    preposition_sp, preposition_word = maybe_preposition
                    preposition += preposition_sp.string + preposition_word.string
            elif preposition_choice == 2:  # e.g. "*"
                maybe_sp, star = some_preposition
                if maybe_sp is not None:
                    preposition = maybe_sp.string
                preposition += star.string

            if percentage:
                number /= 100

            return Proportion(offset, number, percentage, None, preposition)

    def implicit_quantity(self, _pt: peggie.ParseTree, children: Any) -> Quantity:
        (offset, number), maybe_unit_and_preposition = children

        unit = None
        value_unit_spacing = ""
        preposition = ""
        if maybe_unit_and_preposition is not None:
            maybe_unit_sp, unit, maybe_preposition = maybe_unit_and_preposition
            if maybe_unit_sp is not None:
                value_unit_spacing = maybe_unit_sp.string
            if maybe_preposition is not None:
                preposition_sp, preposition_word = maybe_preposition
                preposition = preposition_sp.string + preposition_word.string

        return Quantity(offset, number, unit, value_unit_spacing, preposition)

    def explicit_quantity(self, pt: peggie.Concat, children: Any) -> Quantity:
        (
            open_bracket,
            _sp1,
            (_offset, number),
            maybe_unit,
            _sp2,
            _close_bracket,
            maybe_preposition,
        ) = children

        unit = None
        value_unit_spacing = ""
        if maybe_unit is not None:
            maybe_unit_sp, unit = maybe_unit
            if maybe_unit_sp is not None:
                value_unit_spacing = maybe_unit_sp.string

        preposition = ""
        if maybe_preposition is not None:
            preposition_sp, preposition_word = maybe_preposition
            preposition = preposition_sp.string + preposition_word.string

        return Quantity(
            open_bracket.start, number, unit, value_unit_spacing, preposition
        )

    def reference(self, _pt: peggie.ParseTree, children: Any) -> Reference:
        maybe_quantity_or_proportion, name = children

        quantity_or_proportion: Optional[Union[Quantity, Proportion]] = None
        if maybe_quantity_or_proportion is not None:
            quantity_or_proportion, _sp = maybe_quantity_or_proportion

        return Reference(name, quantity_or_proportion)

    def step(self, _pt: peggie.ParseTree, children: Any) -> Step:
        (
            name,
            _sp1,
            _open,
            _sp2,
            first_input,
            rest_inputs,
            _comma,
            _sp3,
            _close,
        ) = children

        inputs = [first_input]
        for _sp1, _comma, _sp, next_input in rest_inputs:
            inputs.append(next_input)

        return Step(name, inputs)

    def ltr_shorthand(self, _pt: peggie.ParseTree, children: Any) -> Expr:
        reference, steps = children

        for _sp0, _comma, _sp1, step in steps:
            reference = Step(step, [reference])

        return cast(Expr, reference)

    def expr(self, pt: peggie.Alt, children: Any) -> Expr:
        if pt.choice_index in (0, 1):  # step or reference
            return cast(Expr, children)
        else:  # ltr_shorthand
            _open, _sp1, ltr_shorthand, _sp2, _close = children
            return cast(Expr, ltr_shorthand)

    def output_list(self, _pt: peggie.Alt, children: Any) -> List[String]:
        first, rest = children

        out = [first]
        for _sp1, _comma, _sp1, next in rest:
            out.append(next)

        return out

    def stmt(self, _pt: peggie.Alt, children: Any) -> Stmt:
        maybe_target, expr, _eol = children

        output_list = None
        named = False
        if maybe_target is not None:
            output_list, _sp1, colon, _sp2 = maybe_target
            named = colon.string == ":="

        return Stmt(expr, output_list, named)

    def recipe(self, _pt: peggie.Alt, children: Any) -> Recipe:
        _sp, stmts, _eof = children
        return Recipe(stmts)
