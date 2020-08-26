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
)
