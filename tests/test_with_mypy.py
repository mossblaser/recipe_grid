import os

import subprocess


def test_with_mypy() -> None:
    subprocess.run(
        os.path.join(os.path.dirname(__file__), "..", "run_mypy.sh"), check=True
    )
