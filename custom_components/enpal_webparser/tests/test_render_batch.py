"""Tests for incremental Blazor RenderBatch diff parsing (Phase 4).

The fast path parses changed sensor rows straight from the RenderBatch binary
payload so the integration no longer HTTP re-scrapes /deviceMessages on every
server push.
"""
import os

from custom_components.enpal_webparser.api.render_batch import (
    parse_render_batch_strings,
    extract_changed_rows,
    is_patchable_value,
)
from custom_components.enpal_webparser.api.websocket_client import EnpalWebSocketClient
from custom_components.enpal_webparser.utils import parse_enpal_html_sensors, make_id
from custom_components.enpal_webparser.const import DEFAULT_GROUPS

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
RENDER_BATCH_BIN = os.path.join(FIXTURE_DIR, "render_batch_sample.bin")
DEVICE_MESSAGES_HTML = os.path.join(FIXTURE_DIR, "deviceMessages.html")


def _load_batch() -> bytes:
    with open(RENDER_BATCH_BIN, "rb") as f:
        return f.read()


def _load_baseline():
    with open(DEVICE_MESSAGES_HTML, encoding="utf-8") as f:
        html = f.read()
    return parse_enpal_html_sensors(html, list(DEFAULT_GROUPS))


# ---------------------------------------------------------------------------
# String-table decoding
# ---------------------------------------------------------------------------

def test_parse_render_batch_strings_decodes_table():
    strings = parse_render_batch_strings(_load_batch())
    assert strings, "expected a non-empty string table"
    # The change-marker class and known sensor keys must be present.
    assert "dp-flash" in strings
    assert "Battery.DeviceType" in strings
    assert "Battery.Unit.1.Voltage" in strings


def test_parse_render_batch_strings_handles_garbage():
    assert parse_render_batch_strings(b"") == []
    assert parse_render_batch_strings(b"\x00\x01\x02") == []
    assert parse_render_batch_strings(b"x" * 19) == []


# ---------------------------------------------------------------------------
# Row extraction
# ---------------------------------------------------------------------------

def test_extract_changed_rows_from_real_batch():
    rows = extract_changed_rows(parse_render_batch_strings(_load_batch()))
    assert rows, "expected changed rows"

    by_key = {r["key"]: r for r in rows}

    # String sensor without a unit.
    assert by_key["Battery.DeviceType"]["value"] == "Huawei"
    assert by_key["Battery.DeviceType"]["unit"] is None

    # Numeric sensor with a unit.
    assert by_key["Battery.Unit.1.Voltage"]["value"] == "53"
    assert by_key["Battery.Unit.1.Voltage"]["unit"] == "V"

    assert by_key["Power.Consumption.Total"]["value"] == "566"
    assert by_key["Power.Consumption.Total"]["unit"] == "W"

    # Every row carries an ISO-ish timestamp.
    for row in rows:
        assert row["timestamp"] and row["timestamp"].endswith("Z")


def test_extract_changed_rows_synthetic_pattern():
    strings = [
        "tr", "class", "dp-flash", "td",
        "Battery.Unit.1.Voltage", "\n    ", "53", "V", "\n    ", "2026-06-02 15:06:50.331Z",
        "dp-flash", "td",
        "Battery.DeviceType", "\n    ", "Huawei", "\n    ", "2026-06-02 15:06:57.500Z",
    ]
    rows = extract_changed_rows(strings)
    assert len(rows) == 2
    assert rows[0] == {
        "key": "Battery.Unit.1.Voltage",
        "value": "53",
        "unit": "V",
        "timestamp": "2026-06-02 15:06:50.331Z",
    }
    assert rows[1]["key"] == "Battery.DeviceType"
    assert rows[1]["value"] == "Huawei"
    assert rows[1]["unit"] is None


def test_extract_changed_rows_empty_value():
    strings = [
        "dp-flash", "td", "Power.Consumption.Total", "\n    ", "\n    ",
        "2026-06-02 15:06:47.456Z",
    ]
    rows = extract_changed_rows(strings)
    assert len(rows) == 1
    assert rows[0]["value"] == ""
    assert rows[0]["timestamp"] == "2026-06-02 15:06:47.456Z"


def test_is_patchable_value():
    assert is_patchable_value("53")
    assert not is_patchable_value("")
    assert not is_patchable_value(None)
    assert not is_patchable_value("x" * 250)


# ---------------------------------------------------------------------------
# Baseline patching on the client
# ---------------------------------------------------------------------------

def _find(sensors, raw_key):
    """Locate a baseline sensor by its raw dotted key, mirroring the client's
    group-prefix-stripping index logic."""
    target = make_id(raw_key)
    for s in sensors:
        name = s.get("name", "")
        group = s.get("group", "")
        label = name
        prefix = f"{group}: "
        if group and name.startswith(prefix):
            label = name[len(prefix):]
        if make_id(label) == target:
            return s
    return None


def test_apply_diff_updates_unambiguous_sensor():
    baseline = _load_baseline()
    client = EnpalWebSocketClient("http://box.local", groups=list(DEFAULT_GROUPS))
    client._set_baseline(baseline)

    sensor = _find(baseline, "Battery.Unit.1.Voltage")
    assert sensor is not None
    sensor["value"] = "999"  # stale value to be corrected

    client._apply_diff([
        {"key": "Battery.Unit.1.Voltage", "value": "53", "unit": "V",
         "timestamp": "2026-06-02 15:06:50.331Z"},
    ])

    assert sensor["value"] == "53"
    assert sensor["unit"] == "V"
    assert sensor["enpal_last_update"] == "2026-06-02 15:06:50.331Z"


def test_apply_diff_skips_ambiguous_cross_group_keys():
    baseline = _load_baseline()
    client = EnpalWebSocketClient("http://box.local", groups=list(DEFAULT_GROUPS))
    client._set_baseline(baseline)

    # power_ac_phase_a exists in both Inverter and PowerSensor → ambiguous.
    assert len(client._key_index.get(make_id("Power.AC.Phase.A"), [])) > 1

    before = [dict(s) for s in baseline]
    client._apply_diff([
        {"key": "Power.AC.Phase.A", "value": "123", "unit": "W",
         "timestamp": "2026-06-02 15:06:50.331Z"},
    ])
    after = [dict(s) for s in baseline]
    assert before == after, "ambiguous key must not be patched on the fast path"


def test_apply_diff_skips_unknown_key():
    baseline = _load_baseline()
    client = EnpalWebSocketClient("http://box.local", groups=list(DEFAULT_GROUPS))
    client._set_baseline(baseline)

    before = [dict(s) for s in baseline]
    client._apply_diff([
        {"key": "Totally.Unknown.Sensor", "value": "5", "unit": "W",
         "timestamp": "2026-06-02 15:06:50.331Z"},
    ])
    assert [dict(s) for s in baseline] == before
