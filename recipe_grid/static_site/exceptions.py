class StaticSiteError(Exception):
    """Base class for exceptions thrown during website generation."""


class NotADirectoryError(StaticSiteError):
    """Thrown when a path given is not a directory."""


class MultipleReadmeError(StaticSiteError):
    """Thrown when a recipe directory contains multiple index.md or readme.md files."""


class RecipeInDirectoryCompileError(StaticSiteError):
    """Thrown when a recipe found in a directory fails to compile."""


class ReadmeMissingTitleError(StaticSiteError):
    """Thrown when an readme.md file is missing a <h1> level title."""


class ReadmeMalformedTitleError(StaticSiteError):
    """Thrown when an readme.md file's <h1> title contains anything but simple text."""


class RecipeMissingTitleError(StaticSiteError):
    """Thrown when an recipe does not have a title."""


class RecipeMissingServingsError(StaticSiteError):
    """Thrown when an recipe does not have a serving count."""


class MaxServingsLowerThanLargestRecipeError(StaticSiteError):
    """Thrown when max_servings set to less than the largest recipes' native serving count."""


class LinkToExternalFileError(StaticSiteError):
    """Thrown when a file outside the source directory is linked to or referenced."""


class LinkToNonExistentFileError(StaticSiteError):
    """Thrown when a non-file is linked to or referenced."""
