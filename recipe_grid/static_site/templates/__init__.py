import os
from jinja2 import Environment, PackageLoader, select_autoescape

env = Environment(
    loader=PackageLoader("recipe_grid", os.path.join("static_site", "templates")),
    autoescape=select_autoescape(["html", "xml"]),
)

homepage_template = env.get_template("homepage.html")
categories_template = env.get_template("categories.html")
recipe_template = env.get_template("recipe.html")
website_css_template = env.get_template("website.css")

standalone_recipe_template = env.get_template("standalone_recipe.html")

tables_only_css_template = env.get_template("recipe_tables.css")
