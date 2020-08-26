#!/bin/bash

shopt -s globstar

DIR="$(dirname "$0")"

mypy \
    --config-file \
    $DIR/mypy.ini \
    $DIR/tests/**/*.py \
    $DIR/recipe_grid \
    "$@"
