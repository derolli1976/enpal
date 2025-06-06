import pytest
from pathlib import Path

@pytest.fixture
def real_html():
    fixture_path = Path(__file__).parent / "fixtures" / "deviceMessages.html"
    with fixture_path.open("r", encoding="utf-8") as f:
        return f.read()