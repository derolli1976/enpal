#
# Tests for Enpal Webparser - firmware version detection
#
# Unit tests for parse_firmware_version and firmware_supports_websocket.
#
# To run: pytest custom_components/enpal_webparser/tests/test_firmware.py
#

from custom_components.enpal_webparser.utils import (
    parse_firmware_version,
    firmware_supports_websocket,
)


def test_parse_firmware_version_from_html_snippet():
    """Version is extracted from the deviceMessages sidebar anchor text."""
    html = (
        '<a href="" class="nav-item"><span class="navbar-brand"></span>'
        "Solar Rel. 8.46.4-355926 (21.05.2025)</a>"
    )
    assert parse_firmware_version(html) == "8.46.4"


def test_parse_firmware_version_850():
    html = "Solar Rel. 8.50.1-773465 (01.06.2026)"
    assert parse_firmware_version(html) == "8.50.1"


def test_parse_firmware_version_real_html(real_html):
    """The bundled fixture exposes a parseable firmware version."""
    version = parse_firmware_version(real_html)
    assert version is not None
    assert version.startswith("8.")


def test_parse_firmware_version_missing():
    assert parse_firmware_version("") is None
    assert parse_firmware_version(None) is None
    assert parse_firmware_version("<html>no version here</html>") is None


def test_firmware_supports_websocket_true():
    assert firmware_supports_websocket("8.50") is True
    assert firmware_supports_websocket("8.50.1-773465".split("-")[0]) is True
    assert firmware_supports_websocket("8.51.0") is True
    assert firmware_supports_websocket("9.0.0") is True


def test_firmware_supports_websocket_false():
    assert firmware_supports_websocket("8.46.4") is False
    assert firmware_supports_websocket("8.49") is False
    assert firmware_supports_websocket("7.99.9") is False


def test_firmware_supports_websocket_unknown():
    assert firmware_supports_websocket(None) is None
    assert firmware_supports_websocket("") is None
    assert firmware_supports_websocket("not-a-version") is None


def test_firmware_supports_websocket_custom_minimum():
    assert firmware_supports_websocket("8.46", min_version=(8, 40)) is True
    assert firmware_supports_websocket("8.30", min_version=(8, 40)) is False
