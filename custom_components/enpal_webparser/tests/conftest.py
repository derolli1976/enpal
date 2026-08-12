import pytest
from pathlib import Path

@pytest.fixture
def real_html():
    fixture_path = Path(__file__).parent / "fixtures" / "deviceMessages.html"
    with fixture_path.open("r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def real_html_851():
    """deviceMessages page of Enpal firmware 8.51 (extra "Notes" column)."""
    fixture_path = Path(__file__).parent / "fixtures" / "deviceMessages851.html"
    with fixture_path.open("r", encoding="utf-8") as f:
        return f.read()