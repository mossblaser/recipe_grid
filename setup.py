from setuptools import setup, find_packages

setup(
    name="recipe_grid",
    version="2.0",
    packages=find_packages(),
    author="Jonathan Heathcote",
    author_email="mail@jhnet.co.uk",
    description="A tool for representing recipes as dependency-graphs.",
    url="https://github.com/mossblaser/recipe_grid",
    install_requires=["peggie>=0.2.0"],
    entry_points={
        "console_scripts": [
            "recipe-grid=recipe_grid.scripts.recipe_grid:main",
            "recipe-grid-lint=recipe_grid.scripts.recipe_grid_lint:main",
            "recipe-grid-site=recipe_grid.scripts.recipe_grid_site:main",
        ],
    },
)
