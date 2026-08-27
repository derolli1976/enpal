#
# Tests for Enpal Webparser - WallboxBlazorClient status text parsing
#
# The /wallbox page renders the current charge mode and connector status as
# plain text. The status label changed with firmware 8.51.1: 'Status <X>'
# became 'Connector <X>'. Both formats must be recognized, in pre-rendered
# HTML as well as in RenderBatch payloads where label and value can sit in
# separate string-table entries (separated by a VLQ length byte).
#
# To run: pytest custom_components/enpal_webparser/tests/test_wallbox_client.py
#

from custom_components.enpal_webparser.api.wallbox_client import WallboxBlazorClient

extract = WallboxBlazorClient._extract_status_text


def test_status_label_pre_851():
    # Firmware <= 8.51.0: pre-rendered HTML says 'Mode Solar' / 'Status Charging'
    data = b"<h5>Mode Solar</h5><p>Status Charging</p>"
    assert extract(data) == ("Solar", "Charging")


def test_connector_label_8511():
    # Firmware 8.51.1: the status card says 'Connector Charging'
    data = b"<h5>Mode Solar</h5><p>Connector Charging</p>"
    assert extract(data) == ("Solar", "Charging")


def test_connector_label_renderbatch_string_table():
    # In RenderBatch payloads the value is a separate string-table entry,
    # so a length byte sits between label and value.
    data = b"junk\x0aMode \x05Solar\x0aConnector \x08Charging\x0amore"
    assert extract(data) == ("Solar", "Charging")


def test_status_label_wins_over_connector():
    # Old firmware may contain both words; 'Status' stays authoritative.
    data = b"Mode Eco ... Status Connected ... Connector Available"
    assert extract(data) == ("Eco", "Connected")


def test_no_match_returns_none():
    assert extract(b"completely unrelated payload") == (None, None)


def test_invalid_mode_word_is_ignored():
    # 'Mode Unknown' is not a valid charge mode and must not be reported.
    data = b"Mode Unknown ... Connector Charging"
    assert extract(data) == (None, "Charging")

