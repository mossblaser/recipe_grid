import pytest

from typing import Optional

from pathlib import Path

from recipe_grid.static_site.standalone_page import generate_standalone_page


class TestGenerateStandalonePage:
    @pytest.mark.parametrize(
        "markdown",
        ["No title at all", "# Title with no servings count"],
    )
    @pytest.mark.parametrize("scale", [None, 1, 3])
    def test_title_not_required_when_servings_not_given(
        self,
        tmp_path: Path,
        markdown: str,
        scale: Optional[int],
    ) -> None:
        filename = tmp_path / "file.md"

        filename.open("w").write(markdown)

        # Shouldn't crash
        generate_standalone_page(filename, scale=scale)

    def test_servings(self, tmp_path: Path) -> None:
        filename = tmp_path / "file.md"

        filename.open("w").write("# A recipe for 3")

        # Shouldn't crash
        generate_standalone_page(filename, servings=2)

    def test_embed_links(self, tmp_path: Path) -> None:
        filename = tmp_path / "file.md"

        (tmp_path / "something.txt").open("w").write("foobar")

        filename.open("w").write(
            "# A recipe for 3\n" "Check out [foobar](./something.txt)"
        )

        # Shouldn't crash
        html_with_links = generate_standalone_page(filename, embed_local_links=False)
        assert "./something.txt" in html_with_links
        assert "data:text/plain;base64,Zm9vYmFy" not in html_with_links

        html_with_data = generate_standalone_page(filename, embed_local_links=True)
        assert "data:text/plain;base64,Zm9vYmFy" in html_with_data
        assert "./something.txt" not in html_with_data
