#
# Tests for Enpal Webparser - InfluxDB client (expert data source)
#
# Uses a sanitized CSV fixture captured from a real Enpal box (InfluxDB 2.8.0,
# bucket "solar", firmware 8.51.1). Verifies that the Influx rows map onto the
# same entity ids, units and groups as the WebSocket/HTML clients.
#
# To run: pytest custom_components/enpal_webparser/tests/test_influx_client.py
#

from pathlib import Path

import pytest

from custom_components.enpal_webparser.api.influx_client import (
    EnpalInfluxClient,
    parse_influx_csv,
)
from custom_components.enpal_webparser.utils import make_id

FIXTURE = Path(__file__).parent / "fixtures" / "influx_last_values.csv"


@pytest.fixture
def rows():
    return parse_influx_csv(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def client():
    return EnpalInfluxClient("http://192.168.1.50", token="t", org="enpal")


@pytest.fixture
def sensors_by_id(client, rows):
    sensors = client.sensors_from_rows(rows)
    return {make_id(s["name"]): s for s in sensors}


def test_parse_influx_csv_extracts_all_series(rows):
    # 21 rows in the fixture; all carry _field and _value.
    assert len(rows) == 21
    assert rows[0]["_field"] == "Current.Battery"
    assert rows[0]["_measurement"] == "battery"
    assert rows[0]["unit"] == "A"


def test_parse_influx_csv_defensive():
    assert parse_influx_csv("") == []
    assert parse_influx_csv("garbage without commas") == []


def test_entity_ids_match_websocket_mode(sensors_by_id):
    # Same ids as the WS client produces for these dotted keys. friendly_name
    # drops the group prefix when the key already contains the group word.
    assert sensors_by_id["inverter_power_dc_total"]["value"] == "10231"
    assert sensors_by_id["inverter_power_dc_total"]["unit"] == "W"
    assert sensors_by_id["inverter_power_dc_total"]["device_class"] == "power"
    assert sensors_by_id["temperature_battery"]["group"] == "Battery"
    assert "status_wallbox_connected" in sensors_by_id


def test_unit_tag_translation(sensors_by_id):
    # Celcius -> °C, Percent -> %
    temp = sensors_by_id["temperature_battery"]
    assert temp["unit"] == "°C"
    assert temp["device_class"] == "temperature"
    assert temp["value"] == "40.7"  # float noise trimmed
    level = sensors_by_id["energy_battery_charge_level"]
    assert level["unit"] == "%"
    # DEVICE_CLASS_OVERRIDES applies like in the HTML parser.
    assert level["device_class"] == "battery"


def test_wh_to_kwh_conversion(sensors_by_id):
    charged = sensors_by_id["energy_wallbox_connector_1_charged_total"]
    assert charged["unit"] == "kWh"
    assert charged["value"] == "6522.47"
    load = sensors_by_id["energy_battery_charge_load"]
    assert load["unit"] == "kWh"
    assert load["value"] == "10.0"


def test_junk_and_duplicates_are_dropped(client, rows):
    sensors = client.sensors_from_rows(rows)
    ids = [make_id(s["name"]) for s in sensors]
    # measureId has no dotted-key shape
    assert not any("measureid" in i for i in ids)
    # duplicates collapse: Energy.Battery.Charge.Lifetime (battery+inverter),
    # Power.AC.Phase.A(.Inverter) via alias, Power.DC.Total(.Huawei)
    assert len(ids) == len(set(ids))
    assert ids.count("inverter_energy_battery_charge_lifetime") == 1


def test_alias_maps_to_historic_entity_id(sensors_by_id):
    # Power.AC.Phase.A.Inverter aliases back to Power.AC.Phase.A
    assert "powersensor_power_ac_phase_a" in sensors_by_id
    assert "powersensor_power_ac_phase_a_inverter" not in sensors_by_id


def test_influx_only_system_keys_get_site_data_group(sensors_by_id):
    prod = sensors_by_id["site_data_power_production_total"]
    assert prod["group"] == "Site Data"
    assert prod["value"] == "10231"


def test_system_state_expands_into_split_sensors(sensors_by_id):
    # Influx stores only the decimal; bits are synthesized (6 -> 0000000110).
    assert sensors_by_id["inverter_system_state"]["value"].startswith("Decimal: 6")
    assert sensors_by_id["inverter_system_state_decimal"]["value"] == "6"
    assert sensors_by_id["inverter_system_state_flags"]["value"] == (
        "Grid-connected, Grid-connected normally"
    )
    assert sensors_by_id["inverter_system_state_grid_connected"]["value"] == "on"
    assert sensors_by_id["inverter_system_state_standby"]["value"] == "off"


def test_excluded_groups_only_disable(rows):
    client = EnpalInfluxClient(
        "http://192.168.1.50", token="t", org="enpal",
        excluded_groups=["IoTEdgeDevice"],
    )
    by_id = {make_id(s["name"]): s for s in client.sensors_from_rows(rows)}
    assert by_id["iotedgedevice_cpu_load"]["enabled"] is False
    assert by_id["inverter_power_dc_total"]["enabled"] is True


def test_no_value_longer_than_255(client, rows):
    for sensor in client.sensors_from_rows(rows):
        assert len(str(sensor["value"])) <= 255
