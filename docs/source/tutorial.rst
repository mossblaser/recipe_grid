.. _tutorial:

Recipe Grid Tutorial
====================

This tutorial will give you an introduction to Recipe Grid including its recipe
description language and tools for compiling recipes into stand-alone HTML
pages or complete recipe websites.

Recipe description basics
-------------------------

.. highlight:: md

Recipes are not described directly in tabular form. Instead, these tables are
generated from a simple textual description of the recipe. These descriptions
are usually embedded in `Markdown <https://commonmark.org/>`_ documents.

The following example shows a simple recipe Markdown file::

    Boiled egg for 1
    ================

    A fairly boring recipe...

        boil for 3.5 minutes (
            1 egg,
            500ml water,
        )

This is compiled into HTML using:

.. code:: bash

    $ recipe-grid path/to/my_recipe.md

Which produces a file called ``my_recipe.html`` which looks like this:

.. image:: /_static/boiled_egg_example.png

As you can see, the textual recipe description in the indented block in the
Markdown file has been converted into the tabular form (we'll look at this
syntax in greater detail shortly). Aside from these indented blocks, a recipe
is just an ordinary Markdown file which you can structure however you like.

.. note::

    In Markdown indented blocks are usually used for code listings but are
    co-opted by Recipe Grid for recipe descriptions. If you want to include an
    ordinary code block in your recipe, you can do so using a Markdown 'fenced'
    block like so::

        Here is a code listing:

        ```
        print("Hello, world!")
        ```

The ``recipe-grid`` command has a few options which allow us to automatically
rescale the quantities in a recipe. In addition to the ``recipe-grid`` command
(which compiles a single recipe into a standalone HTML page) a other commands
are provided to, for example, produce a static 'recipe book' style website from
a collection of recipes. We'll return to look at these commands and options at
the end of this tutorial.


Recipe description syntax
-------------------------

The central feature of Recipe Grid is its recipe description language which is
compiled into the tabular form which appears in a compiled recipe. Lets take a
look at this language.

For brevity, in the examples below we'll just show the recipe descriptions. To
compile these you'll need to place them in an indented block in a Markdown file
and compile them using the ``recipe-grid`` command as illustrated above.


Ingredients and steps
`````````````````````

Recipe Grid recipes are described in terms of *ingredients* and *steps* which
are carried out on these ingredients.

An ingredient is usually defined by writing a quantity next to a name, for
example ``2 large eggs`` or ``1 tbsp of oil``.

.. note::

    Quantities can be given as either decimal numbers or as fractions. For
    example ``3.5`` and ``3 1/2`` could both be used to mean three-and-a-half.

A step is defined by a description, followed by a pair of parentheses
containing the inputs to that step. For example:

.. recipe::
    :start-new-recipe:
    :show-source:

    fry(2 large eggs, 1 tbsp of oil)

A recipe typically consists of a hierarchy of steps and ingredients, for
example:

.. recipe::
    :start-new-recipe:
    :show-source:

    put in rolls (
        fry until soft (
            slice(1 large onion),
            1 tbsp of oil
        ),
        boil(4 hot dog sausages),
        sliced(4 hot dog rolls),
    )

As in this example, you are free to split the inputs to a step over multiple
lines if this makes the recipe description easier to read.

.. note::

    If your step or ingredient name contains any characters more exciting than
    letters and numbers you must enclose it in single or double quotes. For
    example:

    .. recipe::
        :start-new-recipe:
        :show-source:
    
        "fry (don't allow to burn)" ( 1 can of spam )


Listing ingredients separately
``````````````````````````````

Often when you're translating a traditional recipe into the recipe description
syntax you already have a list of quantities and ingredients. Rather than
manually transcribing these quantities, it is possible to copy-and-paste a list
of ingredients up-front and refer back to these later in the recipe
description. For example:

.. recipe::
    :start-new-recipe:
    :show-source:

    400g of chopped tomatoes
    1 tsp of mixed herbs
    1 onion, finely chopped, fried
    200g of mozzarella, grated
    1 pizza base

    top (
        mozzarella,
        boil down(chopped tomatoes, mixed herbs, onion),
        pizza base,
    )

When referring to an ingredient you only write the ingredient name, e.g. 'mixed
herbs': the quantity and simple prepositions (e.g.  '1 tsp' and 'of') are
omitted.

Additional simple steps, separated by commas, can be defined for ingredients
listed up-front, for example the onion has two steps listed: 'finely chopped'
and 'fried'. In the recipe description later on where we say 'onion' Recipe
Grid will insert both the ingredient and the steps we defined.

.. note::

    The syntax above relies on Recipe Grid being able to distinguish quantities
    and units from an ingredient's name. Recipe Grid understands common cooking
    units (see :ref:`units` for more unformation):
    
        .. rgunitlist::
    
    If you're dealing with an unusual unit which Recipe Grid might not know
    about, or you just prefer to be explicit, you can surround the quantity and
    unit with curly brackets, for example:
    
    .. code:: text
    
        {2 scoops} of ice cream

    By contrast, if your ingredient name might be confused for a unit or
    preposiition you can use quotes around the ingredient name, for example:
    
    .. code:: text
    
        2 "KG Spooner Brand Biscuits".


Sub-recipes
```````````

Recipe Grid allows recipes to be broken up into sub-recipes which can make them
easier to write. For example, we can break the pizza sauce from the previous
recipe into its own sub-recipe like so:

.. recipe::
    :start-new-recipe:
    :show-source:

    pizza sauce = boil down (
        400g chopped tomatoes,
        1 tsp mixed herbs,
        fried(finely chopped(1 onion)),
    )

    top (
        grated(200g mozzarella),
        pizza sauce,
        1 pizza base,
    )

Notice that, once compiled, the sub recipe is seamlessly combined into the
final recipe.

Sometimes it is helpful if a sub recipe is named and called out in the final
recipe; particularly for more complex recipes, or recipes where some parts can
be prepared in advance. Replacing the ``=`` symbol with ``:=`` in our sub
recipe definition will cause Recipe Grid to identify the sub recipe in the
generated table, for example, after modifying the example above we get:

.. recipe::
    :start-new-recipe:

    pizza sauce := boil down (
        400g chopped tomatoes,
        1 tsp mixed herbs,
        fried(finely chopped(1 onion)),
    )

    top (
        grated(200g mozzarella),
        pizza sauce,
        1 pizza base,
    )

.. note::

    The up-front ingredient syntax described in the previous section is
    actually just a short-hand for creating a sub recipes. When a single
    ingredient (with any number of steps acting on it) is defined on its own, a
    sub recipe with the ingredient's name is automatically created.


Splitting recipe components up
``````````````````````````````

Sometimes recipes call for ingredients or sub recipes to be split into parts
which are then used separately. For example in the following recipe for
enchiladas, some of the sauce is mixed with the chicken and some is poured over
the top before baking.

.. recipe::
    :start-new-recipe:
    :show-source:

    tomato sauce = boil down (
        400g chopped tomatoes,
        spices,
    )

    bake until golden (
        pour over(
            fill (
                simmer for 5 minutes (
                    fry (
                        200g chicken,
                        sliced(1 onion),
                    ),
                    2/3 of the tomato sauce,
                ),
                4 tortilla wraps,
            ),
            remaining tomato sauce,
            100g grated cheese,
        )
    )

In this case, Recipe Grid splits the recipe into two tables: one for the tomato
sauce and one for the remainder of the recipe. In the main part of the recipe
the references to the earlier sub recipe contain links to the relevant sub
recipe.

References to sub recipes follow a similar form to ingredients: they begin with
a quantity (e.g. ``1/2`` or ``20g`` or ``remaining``)  followed by an optional
preposition (e.g. 'of the') and then the name of the sub recipe being
referenced.


Sub recipes with multiple outputs
`````````````````````````````````

Sometimes a step may produce multiple things. For example, after boiling some
vegetables you may wish to use both the vegetables and the water they were
boiled in. To do this, you can define a sub recipe to have multiple outputs
like so:

.. recipe::
    :start-new-recipe:
    :show-source:

    boiled veg, veg water = drain reserving water(
        boil(
            carrots,
            peas,
        )
    )

    pour over (
        make gravy (5 tsp of gravy browning, veg water),
        boiled veg,
    )


Mixing prose and recipe tables
``````````````````````````````

For particularly complicated recipes it is possible to split a recipe into sub
recipes which appear at different points in the document. To do this, simply
create multiple indented blocks in your markdown document which define sub
recipes which reference each other. For example::

    Pizza for 2
    ===========

    First you should make some pizza sauce:

        pizza sauce = boil down (
            400g chopped tomatoes,
            1 tsp mixed herbs,
            fried(finely chopped(1 onion)),
        )

    Then once you've done that you can go ahead and make some pizza:

        top (
            grated(200g mozzarella),
            pizza sauce,
            1 pizza base,
        )

Will compile into:

.. image:: /_static/split_recipe_example.png

When recipes are split between indented blocks in this way, references to sub
recipes in other indented blocks are not shown in place but instead shown as a
reference.


Scaling recipes
---------------

Recipe Grid can automatically rescale quantities in recipes. Using the
``recipe-grid`` command, this is achieved by adding the ``--scale`` argument
followed by a scaling factor. For example, to compile a recipe, halving all of
the quantities we would write:

.. code:: bash

    $ recipe-grid --scale 1/2 path/to/recipe.md

.. note::

    When the scaling factor is given as an integer or a fraction, quantities in
    the recipe will be shown as fractions too (where the denominator is
    sensible). Using a decimal number (e.g. ``0.5``) will cause all quantities
    to be shown as decimal numbers.

When a recipe's main title ends with a phrase like ``for 3`` or ``serves 7``,
the ``--servings`` argument can be used instead, taking the desired number of
servings to make (saving hand-calculating the appropriate scaling factor).

.. code:: bash

    $ recipe-grid --servings 3 path/to/recipe.md

In either case, when the recipe is compiled, a subtitle is added indicating any
scaling applied:

.. image:: /_static/scaling_example.png

Sometimes your recipe may contain numbers which ought to be scaled with the
ingredient quantities. For example, in a burger recipe you might have a step
which says 'divide into 4 patties'. To make a number scale with the recipe you
can enclose it in curly brackets, for example:

.. recipe::
    :start-new-recipe:
    :show-source:

    grill for 10 minutes (
        divide into {4} patties (
            mash together(
                450g minced beef,
                finely chopped(1 onion),
                1 tsp mixed herbs,
            )
        )
    )

And then the same recipe scaled up by a factor of two gives:

.. recipe::
    :start-new-recipe:
    :scale: 2

    grill for 10 minutes (
        divide into {4} patties (
            mash together(
                450g minced beef,
                finely chopped(1 onion),
                1 tsp mixed herbs,
            )
        )
    )

The curly bracket syntax can also be used outside of the recipe description
in the rest of the Markdown document.

.. note::

    To get a literal ``{`` or ``}`` character you can use ``{\{}`` or ``{\}}``
    respectively.


Linting
-------

Recipe Grid provides a linting tool, ``recipe-grid-lint``, which checks for
common mistakes within recipes.

For example, given the following recipe::

    Boiled egg for 1
    ================

    A simple recipe, with a simple mistake...

        2 eggs
        500ml water

        boil(egg, water)

The linter will spot that the eggs were never used: in the recipe we mistakenly
referenced 'egg' and not 'eggs'.

.. code:: bash

    $ recipe-grid-lint path/to/recipe.md
    /path/to/recipe.md: Warning: Ingredient 'eggs' was defined but never used. [unused_ingredient]

When no issues are found, the command exits without printing anything.


Generating recipe book static websites
--------------------------------------

As well as compiling individual recipes into standalone HTML pages, Recipe Grid
can also compile collections of recipes into a complete static website,
suitable for use on- or offline.

To generate a recipe website, recipes should be collected together with
filenames ending in ``.md``. If desired, recipes can be grouped into a
directories which and displayed as browsable categories in the generated
website.

A ``index.md`` or ``README.md`` file may optionally be placed alongside the
recipes whose contents is shown on the homepage or category pages.


For example a site might have a directory tree as follows:

.. code:: text

    + README.md
    + pasta/
    | + README.md
    | + spaghetti.md
    | + lasagne.md
    + indian/
    | + dahl.md
    | + curry.md

In this case the top-level ``README.md`` might look as follows::

    My Recipe Website
    =================

    Here are some of my favourite recipes!

The ``README.md`` in the ``pasta/`` directory might contain::

    Pasta
    =====

    Oh I do like pasta dishes! I hope you'll like them too!

A recipe website is then generated using the ``recipe-grid-site`` command as
follows:

.. code:: bash

    $ recipe-grid-site path/to/recipes/dir/ path/to/output/dir/

The generated website can then be opened in a browser and used locally or
uploaded to a static web hosting service and used online.

.. image:: /_static/site_example_home.png

.. image:: /_static/site_example_categories.png

.. image:: /_static/site_example_category.png

.. image:: /_static/site_example_recipe.png
