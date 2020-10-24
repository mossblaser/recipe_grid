Recipe Grid
===========

Recipe Grid is a collection of standalone utilities and also a Python library
for describing recipes in a tabular form, as illustrated by the following
(rather tasty) recipe below for tiffin:

.. image:: /_static/tiffin_example.png

These recipes have several advantages over traditional recipe descriptions:

* Recipes are typically more concise.
* Quantities and method are shown together so no more cross-reference between
  the two while cooking.
* Steps, such as preparing vegetables, are never "hidden" away in an ingredients list 
* Opportunities to carry out steps in parallel, or not, or in different orders are
  easy to spot while still exposing a natural suggested order.

Recipes are described in Markdown files using a convenient to write recipe
description language. For example, the recipe above was generated from the
following description:

.. code:: md

    Tiffin
    ======
    
    A delicious, chocolatey treat.
    
        6 tsp of cocoa powder
        2 tbsp of golden syrup
        1/2 cup of butter
        1/2 cup of sugar
        16oz of digestives
        200g of chocolate
        
        cover(
            mix(
                heat until bubbling (cocoa powder, golden syrup, butter, sugar),
                crush(digestives)
            ),
            melt(chocolate)
        )

Using Recipe Grid
-----------------

The best place to get started is with :ref:`the Recipe Grid tutorial <tutorial>`:

.. toctree::
   :maxdepth: 2
   
   tutorial.rst

More detailed documentation is also provided for the Recipe Grid language and
tools:

.. toctree::
   :maxdepth: 2
   
   markdown.rst
   sphinx.rst
   language_reference.rst



TODO
----


.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   grammar.rst
   data_model.rst
