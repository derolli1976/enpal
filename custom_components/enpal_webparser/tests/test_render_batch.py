"""Tests for incremental Blazor RenderBatch diff parsing (Phase 4).

The fast path parses changed sensor rows straight from the RenderBatch binary
payload so the integration no longer HTTP re-scrapes /deviceMessages on every
server push.
"""
import asyncio
import os
import struct

from custom_components.enpal_webparser.api.render_batch import (
    parse_render_batch_strings,
    extract_change_handler_ids,
    extract_changed_rows,
    extract_event_handlers,
    extract_initial_rows,
    is_patchable_value,
)
from custom_components.enpal_webparser.api.websocket_client import EnpalWebSocketClient
from custom_components.enpal_webparser.utils import parse_enpal_html_sensors, make_id
from custom_components.enpal_webparser.const import (
    DEFAULT_GROUPS,
    SENSOR_KEY_ALIASES,
    SENSOR_KEY_GROUPS,
)

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
RENDER_BATCH_BIN = os.path.join(FIXTURE_DIR, "render_batch_sample.bin")
RENDER_BATCH_851_INITIAL_BIN = os.path.join(
    FIXTURE_DIR, "render_batch_851_initial.bin"
)
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


def test_apply_diff_creates_unknown_key_as_uncategorized():
    """Keys without a SENSOR_KEY_GROUPS entry land in \"Uncategorized\"."""
    baseline = _load_baseline()
    client = EnpalWebSocketClient("http://box.local", groups=list(DEFAULT_GROUPS))
    client._set_baseline(baseline)

    client._apply_diff([
        {"key": "Totally.Unknown.Sensor", "value": "5", "unit": "W",
         "timestamp": "2026-06-02 15:06:50.331Z"},
    ])
    created = _find(client._baseline, "Totally.Unknown.Sensor")
    assert created is not None
    assert created["group"] == "Uncategorized"
    assert created["enabled"] is True
    assert created["value"] == "5"

    # Numeric pseudo-keys from misread rows are not turned into sensors.
    before = len(client._baseline)
    client._apply_diff([
        {"key": "226.3", "value": "1", "unit": "V",
         "timestamp": "2026-06-02 15:06:50.331Z"},
    ])
    assert len(client._baseline) == before


def test_apply_diff_rejects_timestamp_as_value_for_numeric_sensor():
    """Regression for issue #133.

    When a RenderBatch row only changed the timestamp, the unchanged value
    string can be missing from the diff, so the row parser may pick up the
    timestamp as the value.  Such a non-numeric value must never overwrite a
    numeric energy counter, otherwise Home Assistant drops it to "unavailable".
    """
    baseline = _load_baseline()
    client = EnpalWebSocketClient("http://box.local", groups=list(DEFAULT_GROUPS))
    client._set_baseline(baseline)

    sensor = _find(baseline, "Energy.Consumption.Total.Lifetime")
    assert sensor is not None
    assert sensor["device_class"] == "energy"
    good_value = sensor["value"]

    client._apply_diff([
        {"key": "Energy.Consumption.Total.Lifetime",
         "value": "2026-06-02 15:05:10.244Z", "unit": None,
         "timestamp": "2026-06-02 15:05:10.244Z"},
    ])

    # The last good numeric value must be retained.
    assert sensor["value"] == good_value


def test_apply_diff_still_patches_numeric_sensor_with_numeric_value():
    baseline = _load_baseline()
    client = EnpalWebSocketClient("http://box.local", groups=list(DEFAULT_GROUPS))
    client._set_baseline(baseline)

    sensor = _find(baseline, "Energy.Consumption.Total.Lifetime")
    assert sensor is not None

    client._apply_diff([
        {"key": "Energy.Consumption.Total.Lifetime",
         "value": "16360.30", "unit": "kWh",
         "timestamp": "2026-06-02 15:05:10.244Z"},
    ])

    assert sensor["value"] == "16360.30"
    assert sensor["unit"] == "kWh"


def test_apply_diff_allows_nonnumeric_value_for_string_sensor():
    """Non-numeric sensors (serials, states, device types) must still patch."""
    baseline = _load_baseline()
    client = EnpalWebSocketClient("http://box.local", groups=list(DEFAULT_GROUPS))
    client._set_baseline(baseline)

    sensor = _find(baseline, "HW.Cronny.Result")
    assert sensor is not None
    assert sensor.get("device_class") not in {
        "energy", "power", "voltage", "current", "temperature",
        "frequency", "battery", "humidity", "pressure",
    }

    client._apply_diff([
        {"key": "HW.Cronny.Result", "value": "cronny.hw_metrics.fail", "unit": None,
         "timestamp": "2026-06-02 15:05:10.244Z"},
    ])

    assert sensor["value"] == "cronny.hw_metrics.fail"


# ---------------------------------------------------------------------------
# Firmware 8.51: row layout with Notes column and css helper classes
# ---------------------------------------------------------------------------

# String table reconstructed from a real 3.0.3b5 debug log (firmware 8.51).
_851_STRINGS = [
    "onchange", "tr", "class",
    "dp-flash pi-row-validation", "td",
    "SerialNumber.Battery.Unit.2", "colspan", "3", "pi-note-cell", "span",
    "pi-note-text", "tabindex", "0",
    "invalid: SerialNumber.Battery.Unit.2 contains invalid characters",
    "dp-flash pi-row-validation",
    "Cpu.Load", "3", "pi-note-cell", "pi-note-text", "0",
    "invalid: Cpu.Load unit type is incorrect. Expected: None, Value: Percent",
    "dp-flash",
    "Current.Wallbox.Connector.1.Phase.A", "0.02", "A", "text-nowrap",
    "width: 1%;", "18:19:44.00", "pi-note-cell", "pi-note-text", "0",
    "calculated value",
    "dp-flash",
    "Count.Wallbox.Connector.1.Phases.Charging", "3", "text-nowrap", "style",
    "width: 1%;", "18:19:50.50", "pi-note-cell", "pi-note-text", "0",
    "calculated value",
    "dp-flash pi-row-validation",
    "Inverter.Power.Total", "1373", "W", "text-nowrap", "width: 1%;",
    "17:45:58.77", "pi-note-cell", "pi-note-text", "0",
    "more recent value invalid: Time Current between values is too large.",
]


def test_extract_changed_rows_851_layout():
    rows = extract_changed_rows(_851_STRINGS)
    by_key = {r["key"]: r for r in rows}

    # Note-only rows carry no reading and must be skipped.
    assert "SerialNumber.Battery.Unit.2" not in by_key
    assert "Cpu.Load" not in by_key

    assert by_key["Current.Wallbox.Connector.1.Phase.A"] == {
        "key": "Current.Wallbox.Connector.1.Phase.A",
        "value": "0.02",
        "unit": "A",
        "timestamp": "18:19:44.00",
    }
    # Value without a unit, "style" between value cell and timestamp.
    assert by_key["Count.Wallbox.Connector.1.Phases.Charging"]["value"] == "3"
    assert by_key["Count.Wallbox.Connector.1.Phases.Charging"]["unit"] is None
    assert by_key["Count.Wallbox.Connector.1.Phases.Charging"]["timestamp"] == "18:19:50.50"
    # Validation rows that still carry a stale value are extracted.
    assert by_key["Inverter.Power.Total"]["value"] == "1373"
    assert by_key["Inverter.Power.Total"]["unit"] == "W"
    assert len(rows) == 3


# ---------------------------------------------------------------------------
# Firmware 8.51: initial full-page render (no dp-flash markers)
# ---------------------------------------------------------------------------

_KNOWN_KEYS = SENSOR_KEY_GROUPS.keys() | SENSOR_KEY_ALIASES.keys()


def _load_initial_851_batch() -> bytes:
    with open(RENDER_BATCH_851_INITIAL_BIN, "rb") as f:
        return f.read()


def test_extract_initial_rows_from_real_851_batch():
    """The captured initial batch (issue #148 sniffer run) yields the full page."""
    strings = parse_render_batch_strings(_load_initial_851_batch())
    assert len(strings) > 1000

    # The initial render carries no dp-flash rows at all ...
    assert extract_changed_rows(strings) == []

    # ... but the device tables are all there.  73 of the 129 known keys in
    # this capture carry a real reading; the rest are note-only rows
    # (colspan=3, "invalid"/"no value") of a box without an LTE modem.
    rows = extract_initial_rows(strings, _KNOWN_KEYS)
    by_key = {r["key"]: r for r in rows}
    assert len(by_key) >= 70

    assert by_key["Power.DC.Total"]["value"] == "905"
    assert by_key["Power.DC.Total"]["unit"] == "W"
    assert by_key["Power.DC.Total"]["timestamp"] == "14:54:54.03"

    assert by_key["Status.Wallbox.Connected"]["value"] == "1"
    assert by_key["Energy.Grid.Export.Day"]["value"] == "0.15"
    assert by_key["Energy.Grid.Export.Day"]["unit"] == "kWh"

    # Note-only rows (colspan / pi-note-cell right after the key) are skipped.
    assert "SerialNumber.Battery.Unit.2" not in by_key
    assert "Cpu.Load" not in by_key
    assert "LTE.RSSI" not in by_key


def test_extract_initial_rows_ignores_unknown_dotted_strings():
    strings = [
        "EnpalEsc.ExternalInterfaceLayer.LocalPage",  # assembly name, no row shape
        "Power.DC.Total", "905", "W", "   ", "text-nowrap",
        "width: 1%;", "14:54:54.03",
    ]
    rows = extract_initial_rows(strings, _KNOWN_KEYS)
    assert [r["key"] for r in rows] == ["Power.DC.Total"]


def test_extract_initial_rows_detects_unmapped_keys_by_pattern():
    """Keys missing from SENSOR_KEY_GROUPS are still extracted (issue #148,
    hidden Huawei rows like Energy.Battery.Charge.Level.Unit.1)."""
    strings = [
        "Energy.Battery.Charge.Level.Unit.9", "61", "%", "   ", "text-nowrap",
        "width: 1%;", "14:54:54.03",
        # junk that must not become a row: version/number fragments
        "v6.3", "226.3", "2.0.1.3.3b118",
    ]
    rows = extract_initial_rows(strings)
    assert [r["key"] for r in rows] == ["Energy.Battery.Charge.Level.Unit.9"]
    assert rows[0]["value"] == "61"
    assert rows[0]["unit"] == "%"


def test_parse_row_body_stops_at_next_key():
    """A key-shaped string ends the value cell (rows without separators)."""
    strings = [
        "SerialNumber.Inverter", "HV1234567890",
        "Battery.DeviceType", "Huawei", "   ", "text-nowrap",
        "width: 1%;", "14:54:54.03",
    ]
    rows = extract_initial_rows(strings)
    by_key = {r["key"]: r for r in rows}
    # First row has no value terminator before the next key -> skipped.
    assert "SerialNumber.Inverter" not in by_key
    assert by_key["Battery.DeviceType"]["value"] == "Huawei"


def test_extract_rows_merges_initial_and_diff_rows():
    """dp-flash rows win over full-render rows for the same key."""
    client = EnpalWebSocketClient("http://box.local", groups=list(DEFAULT_GROUPS))
    strings = [
        # full-render row
        "Power.DC.Total", "905", "W", "   ", "text-nowrap",
        "width: 1%;", "14:54:54.03",
        # dp-flash diff row for the same key with a newer value
        "dp-flash", "Power.DC.Total", "910", "W", "   ", "text-nowrap",
        "width: 1%;", "14:55:04.03",
        # full-render-only row
        "Status.Wallbox.Connected", "1", "   ", "text-nowrap",
        "width: 1%;", "14:56:35.49",
    ]
    rows = {r["key"]: r for r in client._extract_rows(strings)}
    assert rows["Power.DC.Total"]["value"] == "910"
    assert rows["Status.Wallbox.Connected"]["value"] == "1"


def test_initial_851_batch_populates_site_data_only_baseline():
    """End to end: the captured initial batch fills an almost empty baseline."""
    client = EnpalWebSocketClient("http://box.local", groups=list(DEFAULT_GROUPS))
    client._set_baseline(_site_data_only_baseline())
    before = len(client._baseline)

    strings = parse_render_batch_strings(_load_initial_851_batch())
    client._apply_diff(client._extract_rows(strings))

    created = len(client._baseline) - before
    assert created >= 60

    dc = _find(client._baseline, "Power.DC.Total")
    assert dc is not None
    assert dc["group"] == "Inverter"
    assert dc["value"] == "905"


def test_system_state_row_expands_into_split_sensors():
    """The 8.51 <ul> system-state blob becomes the same split sensors as 8.50."""
    client = EnpalWebSocketClient("http://box.local", groups=list(DEFAULT_GROUPS))
    client._set_baseline(_site_data_only_baseline())

    strings = parse_render_batch_strings(_load_initial_851_batch())
    client._apply_diff(client._extract_rows(strings))

    by_id = {make_id(s["name"]): s for s in client._baseline}
    assert by_id["inverter_system_state_decimal"]["value"] == "6"
    assert by_id["inverter_system_state_flags"]["value"] == (
        "Grid-connected, Grid-connected normally"
    )
    assert by_id["inverter_system_state_standby"]["value"] == "off"
    assert by_id["inverter_system_state_grid_connected"]["value"] == "on"
    # No raw sensor with the oversized HTML blob as state.
    for sensor in client._baseline:
        assert len(str(sensor["value"])) <= 255

    # A second apply patches in place instead of duplicating.
    count = len(client._baseline)
    client._apply_diff([{
        "key": "Inverter.System.State",
        "value": "<ul><li>Decimal: 1</li><li>Bits: 0000000001</li></ul>",
        "unit": None,
        "timestamp": "13:00:00.00",
    }])
    assert len(client._baseline) == count
    assert by_id["inverter_system_state_decimal"]["value"] == "1"
    assert by_id["inverter_system_state_standby"]["value"] == "on"
    assert by_id["inverter_system_state_grid_connected"]["value"] == "off"


def test_system_state_row_respects_group_selection():
    client = EnpalWebSocketClient(
        "http://box.local", groups=["Site Data"], excluded_groups=["Inverter"]
    )
    client._set_baseline(_site_data_only_baseline())
    created = client._apply_system_state_row({
        "key": "Inverter.System.State",
        "value": "<ul><li>Decimal: 6</li><li>Bits: 0000000110</li></ul>",
        "unit": None,
        "timestamp": None,
    })
    # Deselected group: sensors are created but default to disabled.
    assert created > 0
    decimal = next(
        s for s in client._baseline
        if make_id(s["name"]) == "inverter_system_state_decimal"
    )
    assert decimal["enabled"] is False


# ---------------------------------------------------------------------------
# Firmware 8.51: creating baseline sensors from RenderBatch rows
# ---------------------------------------------------------------------------

def _site_data_only_baseline():
    """Simulate the 8.51 HTTP scrape, which only contains the Site Data card."""
    return [s for s in _load_baseline() if s.get("group") == "Site Data"]


def test_apply_diff_creates_sensor_with_known_group():
    baseline = _site_data_only_baseline()
    client = EnpalWebSocketClient("http://box.local", groups=list(DEFAULT_GROUPS))
    client._set_baseline(baseline)

    client._apply_diff([
        {"key": "Current.Wallbox.Connector.1.Phase.A", "value": "0.02",
         "unit": "A", "timestamp": "18:19:44.00"},
        {"key": "Energy.Wallbox.Connector.1.Charged.Total", "value": "12725400",
         "unit": "Wh", "timestamp": "18:19:44.00"},
    ])

    created = _find(client._baseline, "Current.Wallbox.Connector.1.Phase.A")
    assert created is not None
    assert created["group"] == "Wallbox"
    assert created["value"] == "0.02"
    assert created["unit"] == "A"
    assert created["raw_key"] == "Current.Wallbox.Connector.1.Phase.A"

    # Wh values are normalized to kWh like in the HTML parser.
    energy = _find(client._baseline, "Energy.Wallbox.Connector.1.Charged.Total")
    assert energy is not None
    assert energy["unit"] == "kWh"
    assert float(energy["value"]) == 12725.4

    # A second diff patches the created sensor instead of duplicating it.
    count_before = len(client._baseline)
    client._apply_diff([
        {"key": "Current.Wallbox.Connector.1.Phase.A", "value": "0.05",
         "unit": "A", "timestamp": "18:19:54.00"},
    ])
    assert created["value"] == "0.05"
    assert len(client._baseline) == count_before


def test_apply_diff_creates_aliased_inverter_sensor():
    baseline = _site_data_only_baseline()
    client = EnpalWebSocketClient("http://box.local", groups=list(DEFAULT_GROUPS))
    client._set_baseline(baseline)

    client._apply_diff([
        {"key": "Power.Battery.Charge.Max.Inverter", "value": "5000",
         "unit": "W", "timestamp": "16:56:02.58"},
    ])

    # The alias strips the ".Inverter" suffix so the entity id matches 8.50.
    created = _find(client._baseline, "Power.Battery.Charge.Max")
    assert created is not None
    assert created["group"] == "Inverter"
    assert created["value"] == "5000"
    assert created["raw_key"] == "Power.Battery.Charge.Max.Inverter"


def test_apply_diff_creation_respects_group_selection():
    baseline = _site_data_only_baseline()
    client = EnpalWebSocketClient(
        "http://box.local", groups=["Site Data", "Wallbox"],
        excluded_groups=["IoTEdgeDevice"],
    )
    client._set_baseline(baseline)

    client._apply_diff([
        {"key": "Cpu.Load", "value": "12", "unit": "%",
         "timestamp": "18:19:44.00"},
    ])

    # Deselected group: the sensor is created but defaults to disabled.
    created = _find(client._baseline, "Cpu.Load")
    assert created is not None
    assert created["group"] == "IoTEdgeDevice"
    assert created["enabled"] is False


def test_set_baseline_keeps_diff_created_sensors():
    baseline = _site_data_only_baseline()
    client = EnpalWebSocketClient("http://box.local", groups=list(DEFAULT_GROUPS))
    client._set_baseline(baseline)

    client._apply_diff([
        {"key": "Current.Wallbox.Connector.1.Phase.A", "value": "0.02",
         "unit": "A", "timestamp": "18:19:44.00"},
    ])
    assert _find(client._baseline, "Current.Wallbox.Connector.1.Phase.A") is not None

    # The periodic full scrape on 8.51 again returns only Site Data.
    client._set_baseline(_site_data_only_baseline())

    kept = _find(client._baseline, "Current.Wallbox.Connector.1.Phase.A")
    assert kept is not None
    assert kept["value"] == "0.02"

    # And it stays patchable after the merge.
    client._apply_diff([
        {"key": "Current.Wallbox.Connector.1.Phase.A", "value": "0.07",
         "unit": "A", "timestamp": "18:19:54.00"},
    ])
    assert kept["value"] == "0.07"


# ---------------------------------------------------------------------------
# Page toggles (firmware 8.51: "Show unsupported/internal values")
# ---------------------------------------------------------------------------

def _attr_frame(name_idx: int, value_idx: int, event_id: int = 0) -> bytes:
    return struct.pack("<iiiq", 3, name_idx, value_idx, event_id)


def _elem_frame() -> bytes:
    return struct.pack("<iiiq", 1, 0, 0, 0)


def _build_batch(frames, strings) -> bytes:
    """Assemble a minimal RenderBatch binary (blobs, frames, table, footer)."""
    buf = bytearray()
    offsets = []
    for s in strings:
        offsets.append(len(buf))
        data = s.encode("utf-8")
        buf.append(len(data))  # VLQ, all test strings < 128 bytes
        buf += data
    frames_offset = len(buf)
    buf += struct.pack("<i", len(frames))
    for frame in frames:
        buf += frame
    frames_end = len(buf)
    string_table_offset = len(buf)
    for off in offsets:
        buf += struct.pack("<i", off)
    buf += struct.pack("<5i", 0, frames_offset, frames_end, 0, string_table_offset)
    return bytes(buf)


_TOGGLE_STRINGS = [
    "input", "class", "form-check-input", "id",
    "showUnsupported_Battery", "type", "checkbox", "onchange",
    "showInternal_Battery", "showUnsupported_IoTEdgeDevice",
]

_TOGGLE_FRAMES = [
    _elem_frame(),
    _attr_frame(1, 2),        # class="form-check-input"
    _attr_frame(3, 4),        # id="showUnsupported_Battery"
    _attr_frame(5, 6),        # type="checkbox"
    _attr_frame(7, -1, 42),   # onchange -> handler 42
    _elem_frame(),
    _attr_frame(3, 8),        # id="showInternal_Battery"
    _attr_frame(7, -1, 43),
    _elem_frame(),
    _attr_frame(3, 9),        # id="showUnsupported_IoTEdgeDevice"
    _attr_frame(7, -1, 44),
    _elem_frame(),
    _attr_frame(7, -1, 99),   # handler without a DOM id -> ignored
]


def test_extract_event_handlers_finds_checkbox_toggles():
    raw = _build_batch(_TOGGLE_FRAMES, _TOGGLE_STRINGS)
    assert extract_event_handlers(raw) == {
        "showUnsupported_Battery": 42,
        "showInternal_Battery": 43,
        "showUnsupported_IoTEdgeDevice": 44,
    }


def test_extract_event_handlers_handles_garbage():
    assert extract_event_handlers(b"") == {}
    assert extract_event_handlers(b"\x00" * 25) == {}
    handlers = extract_event_handlers(_load_batch())
    assert isinstance(handlers, dict)


# Diff batch: the box disposed and recreated all onchange handlers. Fresh ids
# appear in the same DOM order, but without id attributes.
_TOGGLE_DIFF_FRAMES = [
    _attr_frame(7, -1, 142),
    _attr_frame(7, -1, 143),
    _attr_frame(7, -1, 144),
    _attr_frame(7, -1, 199),
]


def test_extract_change_handler_ids_ordered():
    raw = _build_batch(_TOGGLE_FRAMES, _TOGGLE_STRINGS)
    assert extract_change_handler_ids(raw) == [42, 43, 44, 99]

    raw_diff = _build_batch(_TOGGLE_DIFF_FRAMES, _TOGGLE_STRINGS)
    assert extract_change_handler_ids(raw_diff) == [142, 143, 144, 199]


def test_extract_change_handler_ids_handles_garbage():
    assert extract_change_handler_ids(b"") == []
    assert extract_change_handler_ids(b"\x00" * 25) == []


def test_collect_toggle_handlers_remaps_by_position():
    client = EnpalWebSocketClient(
        "http://box.local", groups=["Battery"], excluded_groups=["IoTEdgeDevice"]
    )

    # Initial batch: learn ids and positions.
    client._collect_toggle_handlers(_build_batch(_TOGGLE_FRAMES, _TOGGLE_STRINGS))
    assert client._toggle_handlers == {
        "showUnsupported_Battery": 42,
        "showInternal_Battery": 43,
    }
    assert client._toggle_positions == {
        "showUnsupported_Battery": 0,
        "showInternal_Battery": 1,
    }
    assert client._change_handler_count == 4

    # Diff batch without id attributes: fresh ids are mapped by position.
    client._collect_toggle_handlers(_build_batch(_TOGGLE_DIFF_FRAMES, _TOGGLE_STRINGS))
    assert client._toggle_handlers == {
        "showUnsupported_Battery": 142,
        "showInternal_Battery": 143,
    }


def test_collect_toggle_handlers_skips_mismatched_diff():
    client = EnpalWebSocketClient(
        "http://box.local", groups=["Battery"], excluded_groups=["IoTEdgeDevice"]
    )
    client._collect_toggle_handlers(_build_batch(_TOGGLE_FRAMES, _TOGGLE_STRINGS))

    # A diff batch with a different handler count must not remap.
    short_diff = _build_batch(_TOGGLE_DIFF_FRAMES[:2], _TOGGLE_STRINGS)
    client._collect_toggle_handlers(short_diff)
    assert client._toggle_handlers["showUnsupported_Battery"] == 42


def test_activate_next_toggle_skips_done_and_exhausted():
    client, sent, _ = _toggle_client_with_fake_ws()

    # Acknowledged toggles are never clicked again.
    client._toggles_done.add("showUnsupported_Battery")
    asyncio.run(client._activate_next_toggle())
    assert sent == []

    # Exhausted toggles are skipped even with a fresh handler id.
    client._toggles_done.clear()
    client._toggle_attempts["showUnsupported_Battery"] = 8
    asyncio.run(client._activate_next_toggle())
    assert sent == []


def test_renderer_interop_ref_only_from_attach_call():
    client = EnpalWebSocketClient("http://box.local", groups=["Battery"])
    assert client._renderer_interop_id == 1

    # Radzen chart refs (observed as objects 2..4) must not overwrite the ref.
    client._try_capture_renderer_interop_id(
        "Radzen.createChart",
        '[{"__internalId": "4a5c597b"}, {"__dotNetObject": 4}]',
    )
    assert client._renderer_interop_id == 1

    # Only attachWebRendererInterop carries the renderer object.
    client._try_capture_renderer_interop_id(
        "Blazor._internal.attachWebRendererInterop",
        '[1, {"__dotNetObject": 1}, {}, {}]',
    )
    assert client._renderer_interop_id == 1

    client._try_capture_renderer_interop_id(
        "Blazor._internal.attachWebRendererInterop",
        '[1, {"__dotNetObject": 7}, {}, {}]',
    )
    assert client._renderer_interop_id == 7


def test_collect_toggle_handlers_filters_groups():
    client = EnpalWebSocketClient(
        "http://box.local", groups=["Battery", "Site Data"],
        excluded_groups=["IoTEdgeDevice"],
    )
    raw = _build_batch(_TOGGLE_FRAMES, _TOGGLE_STRINGS)

    client._collect_toggle_handlers(raw)

    # IoTEdgeDevice is deselected, its toggle is ignored.
    assert client._toggle_handlers == {
        "showUnsupported_Battery": 42,
        "showInternal_Battery": 43,
    }


def test_activate_next_toggle_one_per_batch_and_retry():
    client = EnpalWebSocketClient("http://box.local", groups=["Battery"])
    sent = []

    async def fake_send(msg):
        sent.append(msg)

    client._send_message = fake_send

    class FakeWS:
        closed = False

    client.ws = FakeWS()
    client.connected = True
    client._circuit_started = 0.0  # circuit old enough for clicks
    client._toggle_handlers = {
        "showUnsupported_Battery": 42,
        "showInternal_Battery": 43,
    }

    # One checkbox per RenderBatch cycle.
    asyncio.run(client._activate_next_toggle())
    assert len(sent) == 1
    asyncio.run(client._activate_next_toggle())
    assert len(sent) == 2
    asyncio.run(client._activate_next_toggle())
    assert len(sent) == 2  # nothing pending

    # The dispatch goes through DispatchEventAsync with the handler id.
    msg = sent[0]
    assert msg[3] == "BeginInvokeDotNetFromJS"
    assert msg[4][2] == "DispatchEventAsync"
    assert '"eventHandlerId": 42' in msg[4][4]
    assert '"eventName": "change"' in msg[4][4]

    # A re-render assigned a new handler id -> the toggle is clicked again.
    client._toggle_handlers["showUnsupported_Battery"] = 52
    asyncio.run(client._activate_next_toggle())
    assert len(sent) == 3
    assert '"eventHandlerId": 52' in sent[2][4][4]


def test_checkbox_change_payload_matches_browser_format():
    """ChangeEventArgs must be {"value": true} - any extra field (e.g. the
    former "type": "change") makes the box reject the dispatch (issue #148)."""
    import json as json_mod

    client, sent, _ = _toggle_client_with_fake_ws()
    asyncio.run(client._send_checkbox_change("showUnsupported_Battery", 42))

    descriptor, event_args = json_mod.loads(sent[0][4][4])
    assert descriptor == {
        "eventHandlerId": 42,
        "eventName": "change",
        "eventFieldInfo": None,
    }
    assert event_args == {"value": True}


def _toggle_client_with_fake_ws():
    import time

    client = EnpalWebSocketClient("http://box.local", groups=["Battery"])
    sent = []

    async def fake_send(msg):
        sent.append(msg)

    client._send_message = fake_send

    class FakeWS:
        closed = False

    client.ws = FakeWS()
    client.connected = True
    client._circuit_started = 0.0
    client._toggle_handlers = {"showUnsupported_Battery": 42}
    return client, sent, time


def test_activate_next_toggle_waits_for_stable_circuit():
    client, sent, time_mod = _toggle_client_with_fake_ws()

    # Not connected yet (initial batch during connect()) -> no click.
    client.connected = False
    asyncio.run(client._activate_next_toggle())
    assert sent == []

    # Connected, but circuit younger than the minimum age -> no click.
    client.connected = True
    client._circuit_started = time_mod.monotonic()
    asyncio.run(client._activate_next_toggle())
    assert sent == []

    # Circuit old enough -> click goes out.
    client._circuit_started = 0.0
    asyncio.run(client._activate_next_toggle())
    assert len(sent) == 1


def test_activate_next_toggle_respects_disable_flag():
    client, sent, _ = _toggle_client_with_fake_ws()
    client._toggles_disabled = True
    asyncio.run(client._activate_next_toggle())
    assert sent == []


def test_maybe_disable_toggles_blames_recent_click_only():
    import time

    client = EnpalWebSocketClient("http://box.local", groups=["Battery"])

    # No click sent yet -> a circuit death is not our fault.
    client._maybe_disable_toggles("server closed the circuit")
    assert client._toggles_disabled is False

    # Click long ago -> still not our fault.
    client._last_toggle_sent = time.monotonic() - 300
    client._maybe_disable_toggles("server closed the circuit")
    assert client._toggles_disabled is False

    # Click moments ago -> disable for the rest of the runtime.
    client._last_toggle_sent = time.monotonic()
    client._maybe_disable_toggles("server closed the circuit")
    assert client._toggles_disabled is True


def test_is_connected_detects_dead_socket():
    client = EnpalWebSocketClient("http://box.local", groups=["Battery"])

    class FakeTask:
        def done(self):
            return False

    class FakeWS:
        closed = False

    client.connected = True
    client.ws = FakeWS()
    client._read_task = FakeTask()
    assert client.is_connected() is True

    # A closed socket or finished read loop means the circuit is dead even
    # though connect() once succeeded.
    client.ws.closed = True
    assert client.is_connected() is False

    client.ws.closed = False
    client._read_task.done = lambda: True
    assert client.is_connected() is False
