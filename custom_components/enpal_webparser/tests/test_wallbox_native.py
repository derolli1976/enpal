#
# Tests for Enpal Webparser - native wallbox sensors (firmware 8.50+)
#
# Verifies that the wallbox charge mode and connection state are sourced from
# the main /deviceMessages coordinator, including auto-detection of the source
# sensor keys.
#
# To run: pytest custom_components/enpal_webparser/tests/test_wallbox_native.py
#

from pathlib import Path
from types import SimpleNamespace

from custom_components.enpal_webparser.utils import make_id, parse_enpal_html_sensors
from custom_components.enpal_webparser.sensor import (
    _find_wallbox_source,
    WallboxNativeModeSensor,
    WallboxNativeStatusSensor,
)
from custom_components.enpal_webparser.const import (
    WALLBOX_MODE_SOURCE_CANDIDATES,
    WALLBOX_STATUS_SOURCE_CANDIDATES,
)


def _load_850_wallbox_sensors():
    fixture = Path(__file__).parent / "fixtures" / "deviceMessages_wallbox_850.html"
    html = fixture.read_text(encoding="utf-8")
    return parse_enpal_html_sensors(html, ["Wallbox"])


def test_850_fixture_exposes_mode_and_status_keys():
    sensors = _load_850_wallbox_sensors()
    keys = {make_id(s["name"]) for s in sensors}
    assert "wallbox_mode_charge_connector_1" in keys
    assert "status_wallbox_connector_1" in keys


def test_find_wallbox_source_auto_detects_mode():
    sensors = _load_850_wallbox_sensors()
    key = _find_wallbox_source(sensors, "auto", WALLBOX_MODE_SOURCE_CANDIDATES)
    assert key == "wallbox_mode_charge_connector_1"


def test_find_wallbox_source_auto_detects_status():
    sensors = _load_850_wallbox_sensors()
    key = _find_wallbox_source(sensors, None, WALLBOX_STATUS_SOURCE_CANDIDATES)
    # Connector.1 (Available/Charging) reflects the vehicle/charge state.
    # Status.Wallbox.Connected is intentionally NOT a candidate (it only means
    # a wallbox is attached, not whether a vehicle is connected/charging).
    assert key == "status_wallbox_connector_1"
    assert "status_wallbox_connected" not in WALLBOX_STATUS_SOURCE_CANDIDATES


def test_find_wallbox_source_respects_configured_override():
    sensors = _load_850_wallbox_sensors()
    key = _find_wallbox_source(
        sensors, "status_wallbox_connector_1", WALLBOX_STATUS_SOURCE_CANDIDATES
    )
    assert key == "status_wallbox_connector_1"


def test_find_wallbox_source_returns_none_when_missing():
    key = _find_wallbox_source([], "auto", WALLBOX_MODE_SOURCE_CANDIDATES)
    assert key is None


def test_native_mode_sensor_returns_raw_value():
    sensors = _load_850_wallbox_sensors()
    coordinator = SimpleNamespace(data=sensors)
    sensor = WallboxNativeModeSensor(coordinator, "wallbox_mode_charge_connector_1")
    assert sensor.native_value == "Solar"
    assert sensor.unique_id == "wallbox_mode"
    assert sensor.name == "Wallbox Lademodus"


def test_native_status_sensor_lowercases_value():
    sensors = _load_850_wallbox_sensors()
    coordinator = SimpleNamespace(data=sensors)
    sensor = WallboxNativeStatusSensor(coordinator, "status_wallbox_connector_1")
    # "Charging" must be normalized to "charging" for the power-zeroing logic.
    assert sensor.native_value == "charging"
    assert sensor.unique_id == "wallbox_status"
    assert sensor.name == "Wallbox Status"


def test_native_sensor_returns_none_when_key_absent():
    coordinator = SimpleNamespace(data=[])
    sensor = WallboxNativeModeSensor(coordinator, "wallbox_mode_charge_connector_1")
    assert sensor.native_value is None
