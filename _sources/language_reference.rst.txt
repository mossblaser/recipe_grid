.. _language_reference:

Recipe Description Language Reference
=====================================

This page provides a detailed and relatively low-level description of the
recipe description language accepted by Recipe Grid. 

Unlike the formal definition of the recipe description language
(:ref:`grammar`), this description is intended for human consumption and so its
description differs slightly in structure and rigour in the name of easier
understanding.

.. note::

    For a high-level, tutorial introduction to the recipe description language,
    you may prefer :ref:`the tutorial <tutorial>`.

.. note::

    It may be helpful to be aware of :ref:`the Recipe Grid data model
    <data_model>` to understand certain details below.



.. highlight:: bnf


Recipe Building Blocks
----------------------

Ingredients
```````````

::

    Ingredient ::= [Quantity ["of" | "of the"]] String

An ingredient is defined by an optional quantity and proposition, followed by a
name.

Aside from display purposes, an ingredient's name may be used to infer the name
for a sub recipe involving only this ingredient but otherwise has no special
meaning.

The optional preposition ('of' or 'of the') is allowed for readability and does
not form part of the ingredient name.

When no quantity is given, the ingredient is treated as unscaled. This is
useful for ingredients such as seasonings where no specific quantity is given.


Examples:

* ``salt``
* ``2 onions``
* ``1tsp of chilli powder``

References
``````````

::

    Reference ::= [(Quantity | Proportion) ["of" | "of the"]] String

A reference to a sub recipe output consists of an optional quantity or
proportion and preposition and then the name of the sub recipe output being
referenced.

The String at the end of the reference must (case insensitively) match a
previously defined sub recipe output name.

.. note::

    There is a (potential) ambiguity between what is a reference and what is an
    ingredient, for example "Spam" or "100g of the spam" could both plausibly
    be an ingredient or a reference. This ambiguity is resolved by determining
    if the name provided has already been defined as a sub recipe output. If it
    has then the input is parsed as a reference, otherwise it is parsed as an
    ingredient.

When a Quantity or Proportion are not given, the reference is assumed to
consume the whole of the referenced sub recipe. When a Quantity or Proportion
are given, the reference consumes only the specified amount, leaving the
remainder to be consumed by other references.

.. note::

    Unitless Quantities and non-percentage Proportions present a potential
    ambiguity (e.g. is '1/2 onion' a reference to half an onion (i.e. 1/2 is
    a Quantity) or half of the total quantity of onions (i.e. 1/2 is a
    Proportion)).

    The ambiguity is resolved as follows: when a number is immediately followed
    by a preposition (i.e. "of" or "of the") or by an asterisk ("*"), it is
    treated as a proportion. Otherwise, the number is treated as a unitless
    quantity.

References are substituted for the referenced sub recipes (i.e. inlined) when
the reference is the only reference to that sub recipe, the sub recipe has only
one output and the whole amount of that sub recipe is consumed.

Inlining is not performed when referencing a sub recipe defined within a
different block in documents which divide a recipe into multiple blocks.

Examples:

* ``spam`` (the whole of sub recipe 'spam')
* ``2 tomatoes`` (2 of the unitless sub recipe 'tomatoes')
* ``100g cheese`` (100g of the sub recipe 'cheese')
* ``1/2 of the eggs`` (half of the sub recipe 'eggs')
* ``1/2 * eggs`` (half of the sub recipe 'eggs')
* ``50% pastry`` (half of the sub recipe 'pastry')
* ``remaining pastry`` (any remaining amount of the sub recipe 'pastry')

Steps
`````

::

    Step ::= String "(" Expression ("," Expression)* [","]  ")"

A step consists of a String describing the step followed by a parenthesised,
comma-delimited list of input Expressions (i.e. other Steps, Ingredients or
References). There must always be at least one input.

.. note::

    Steps may include line breaks between Expressions within the perenthesised
    list of inputs. (Normally line breaks are not allowed.)

Examples:

* ``whip until thick (double cream)``
* ``fry (1 egg, oil)``


Quantities
``````````

::

    Quantity ::= ImplicitQuantity | ExplicitQuantity
    ImplicitQuantity ::= Number [KnownUnit]
    ExplicitQuantity ::= "{" Number [StaticString] "}"

A quantity with optional unit.

When a known unit is used, no surrounding curly braces are required. The
following (case insensitive) unit names may be used (see :ref:`units` for
details):

    .. rgunitlist::

When a custom unit is used (or just to be more explicit) the explicit quantity
syntax may be used where the number and unit are surrounded by curly braces.

.. note::

    There is a potential for ambiguity between the explicit syntax here and the
    ScaledValueString syntax. The input is always parsed as an ExplicitQuantity
    when it appears at the start of an Ingredient or Reference and starts with
    a Number. To force a ScaledValueString in this case, you could add ``""``
    (an empty string) before the ScaledValueString.

Examples:

* ``10``
* ``2 tsp``
* ``{2 tsp}``
* ``{2 large sacks}``

Proportions
```````````

::

    Proportion ::= (Number ["*" | "%"]) | Remainder
    Remainder ::= "remaining" | "remainder" | "rest" | "left over"

A relative proportion of a quantity. Either a Number, optionally followed by a
asterisk (``*``) or followed by a percent symbol (``%``), or a phrase meaning
'remainder'.

When a Number is given followed by nothing or by a asterisk (``*``), the
proportion is interpreted as a number in the range 0.0 (none) and 1.0 (all).

When the Number is followed by a percent symbol (``%``) it is interpreted as a
percentage (i.e. 0.0 means None and 100.0 means all).

Finally, when a Remainder phrase (e.g. 'remaining') is given, the proportion is
interpreted to mean 'all of the substance which has not already been accounted
for'.

.. note::

    See the note about how ambiguities between Proportions and Quantities in
    References are resolved in the References section above.

Examples:

* ``0.5``
* ``0.5 *``
* ``50%``
* ``remaining``

Top-Level Structure
-------------------

Expressions
```````````

::

    Expression ::= Ingredient | Reference | Step | "(" LTRExpression ")"

An expression represents a sub tree within a recipe. Typically these are
Ingredients, References and Steps defined using the syntax defined above.

If desired, a Left-to-Right expression (e.g. "2 onions, chopped, fried") may be
used but it must be wrapped in parentheses.

Examples:

* ``1 can of spam``
* ``boil(egg)``
* ``(2 onions, chopped, fried)``


Left-to-Right Expressions
`````````````````````````

::

    LTRExpression ::= Expression ("," String)*

An Expression optionally processed by a series of comma-delimited steps. Each
comma-delimited String following the Expression is turned into a step taking
the item to its left as its only input.

The left-to-right expression syntax is provided to make it more natural to
express cases where an ingredient has a series of steps applied to it (and only
it). For example instead of writing "fry(chop(2 onions))" you can write "2
onions, chop, fry".

Examples:

* ``banana, peeled``
* ``2 onions, chopped, fried``
* ``fry(bacon, oil), chop``
* ``1 can of spam`` (no following steps, still technically a LTR expression)


Statements
``````````

::

    Statement ::= [OutputList ("=" | ":=")] LTRExpression EndOfLine
    OutputList ::= String ("," String)+

A Statement defines a tree within a recipe which might (or might not) define
sub recipe.

A sub recipe is defined if an OutputList is given or when the LTRExpression
defines a recipe tree containing any number of Steps and a single Ingredient.

When an output list is given, a sub recipe with the named outputs is created.
The choice between ":=" and "=" defines whether, if substituted for a reference
(inlined), the sub recipe should be shown with a title and thick border or not
(respectively).

When no output list is given and the LTRExpression contains only a single
Ingredient (e.g. "1 can of spam" or "2 onions, sliced, fried") a sub recipe
with a single output with the name inferred from the Ingredient is created. In
this special case, the sub recipe output name is always omitted in rendered
outputs since it should be obvious from the ingredient's name.

In all other cases, no sub recipe is defined (though the tree of Steps,
Ingredients and References will still be added to the final recipe).

Examples:

* ``1 onion, chopped, fried`` (implicitly defines a sub recipe called 'onion')
* ``mixed herbs = mix(basil, origarno, thyme)`` (defines a sub recipe called
  'mixed herbs')
* ``sauce := boil down(tomatoes, herbs)`` (defines a sub recipe called 'sauce'
  which will be outlined and labelled in the final recipe)
* ``boiled veg, veg water = drain reserving water (boil(300g veg, 1l water))``
  (defines a sub recipe with two outputs, 'boiled veg' and 'veg water)
* ``fry(egg, oil)`` (does *not* implicitly define a sub recipe as multiple
  ingredients involved)


Recipe Descriptions
```````````````````

::

    RecipeDescription ::= Statement+

The root of the grammar, a series of statements.



Literal Values
--------------


Numbers
```````

::

    Number ::= Decimal | Fraction
    Decimal ::= DIGITS ["." DIGITS]
    Fraction ::= [DIGITS] DIGITS "/" DIGITS

Numbers may be given as integers (e.g. "123"), decimal numbers (e.g. "1.3"),
two part fractions (e.g. "4/3") or three part fractions (e.g. "1 1/3").

Examples:

* ``123``
* ``1.23``
* ``1/3``
* ``1 2/3``


Strings
```````

::

    String ::= (StaticString | ScaledValueString)+
    StaticString ::= (UnquotedString | SingleQuotedString | DoubleQuotedString)+

There are four kinds of strings matched by String:

UnquotedString
    A naked string, without any quotes around it. It may be made up of any
    series of characters excluding ``"',:=/(){}`` and starting with any
    non-whitespace character and ends with any non-whitespace character. There
    are no escape characters. UnquotedStrings are treated as plain strings.

    Example: ``this is a string with 41 characters in it``

SingleQuotedString
    A string enclosed in single quotes (``'``). May contain single-character
    backslash escape sequences (e.g. ``\'``). SingleQuotedStrings are treated
    as plain strings.

    Example: ``'this is a \'SingleQuotedString\''``

DoubleQuotedString
    A string enclosed in double quotes (``"``). Identical to SingleQuotedString
    except for the type of quotes.

    Example: ``"this is a \"DoubleQuotedString\""``

ScaledValueString
    A string enclosed in curly braces (``{`` and ``}``). Like
    SingleQuotedString and DoubleQuotedString, single character backslash escape
    sequences are supported. Unlike all other string types, substrings
    containing Numbers will be scaled along with all Quantities in the recipe.

    Example: ``{divide into 8 burgers}``

    In the example above, the number (8) will be scaled with the recipe. For
    example if the recipe is halved, it will be replaced with 4.

A String (or StaticString) may consist of any sequence of adjacent string types
which will be concatenated together in the parsed string literal, including any
whitespace between them. For example the string ``pack of {8} hot dog rolls
"(pre-sliced)"`` will be parsed as a string literal containing ``pack of 8 hot
dog rolls (pre-sliced)`` where the '8' is a number which will be rescaled with
the recipe.

See also :py:mod:`recipe_grid.scaled_value_string`.
