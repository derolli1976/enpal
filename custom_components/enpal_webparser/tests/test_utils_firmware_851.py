"""Parsing of the deviceMessages page as rendered by Enpal firmware 8.51.

Firmware 8.51 added a "Notes" column to every sensor table and renamed several
inverter data points (see issue #148). Fixture: Solar Rel. 8.51.0-955735.
"""

from custom_components.enpal_webparser.utils import (
    firmware_supports_websocket,
    make_id,
    parse_enpal_html_sensors,
    parse_firmware_version,
)

GROUPS = ["Site Data", "IoTEdgeDevice", "Inverter", "Battery", "PowerSensor", "Wallbox"]


def _by_id(sensors):
    return {make_id(s["name"]): s for s in sensors}


def test_firmware_version_is_detected(real_html_851):
    version = parse_firmware_version(real_html_851)
    assert version == "8.51.0"
    assert firmware_supports_websocket(version) is True


def test_note_rows_are_not_parsed_as_values(real_html_851):
    sensors = parse_enpal_html_sensors(real_html_851, groups=GROUPS)

    assert sensors
    for sensor in sensors:
        value = sensor["value"]
        assert not value.startswith("missing:")
        assert not value.startswith("invalid:")
        assert "ProcessImageValueKey" not in value
        assert len(value) <= 255


def test_sensor_without_value_is_omitted(real_html_851):
    """Cpu.Load only has a validation note, so no sensor must be produced."""
    sensors = _by_id(parse_enpal_html_sensors(real_html_851, groups=GROUPS))

    assert "iotedgedevice_cpu_load" not in sensors
    assert "iotedgedevice_memory_usage" not in sensors
    assert "powersensor_power_factor" not in sensors


def test_values_and_units_are_still_parsed(real_html_851):
    sensors = _by_id(parse_enpal_html_sensors(real_html_851, groups=GROUPS))

    power_dc = sensors["inverter_power_dc_total_huawei"]
    assert power_dc["value"] == "768"
    assert power_dc["unit"] == "W"
    assert power_dc["device_class"] == "power"

    # Wh is still normalized to kWh with the extra Notes column present.
    charged = sensors["energy_wallbox_connector_1_charged_total"]
    assert charged["value"] == "12665.76"
    assert charged["unit"] == "kWh"


def test_renamed_inverter_keys_keep_their_legacy_ids(real_html_851):
    sensors = _by_id(parse_enpal_html_sensors(real_html_851, groups=["Inverter"]))

    # Power.AC.Phase.A.Inverter must not create a second entity.
    assert "inverter_power_ac_phase_a" in sensors
    assert "power_ac_phase_a_inverter" not in sensors
    assert sensors["inverter_power_ac_phase_a"]["value"] == "-218"

    assert sensors["inverter_energy_battery_charge_day"]["value"] == "0.2"
    assert sensors["inverter_energy_battery_discharge_day"]["value"] == "3.02"
    assert sensors["inverter_power_battery_charge_discharge"]["value"] == "3"
    assert sensors["inverter_power_battery_charge_max"]["value"] == "5000"
    assert sensors["inverter_power_battery_discharge_max"]["value"] == "5000"
    assert "inverter_mode_forcible_charge_discharge" in sensors


def test_inverter_system_state_is_expanded(real_html_851):
    """8.51 renders the state as a readable list instead of one raw bitfield."""
    sensors = _by_id(parse_enpal_html_sensors(real_html_851, groups=["Inverter"]))

    assert sensors["inverter_system_state_decimal"]["value"] == "6"
    assert sensors["inverter_system_state_flags"]["value"] == (
        "Grid-connected, Grid-connected normally"
    )
    assert sensors["inverter_system_state_grid_connected"]["value"] == "on"
    assert sensors["inverter_system_state_standby"]["value"] == "off"


def test_wallbox_status_source_is_still_detected(real_html_851):
    sensors = _by_id(parse_enpal_html_sensors(real_html_851, groups=["Wallbox"]))

    assert sensors["status_wallbox_connector_1"]["value"] == "Preparing"
    assert sensors["wallbox_mode_charge_connector_1"]["value"] == "Fast"


def test_calculated_current_sensors_are_added(real_html_851):
    """8.51 still omits Current.Phase.*, so they must be derived from P and U."""
    sensors = _by_id(parse_enpal_html_sensors(real_html_851, groups=GROUPS))

    for phase in ("a", "b", "c"):
        current = sensors[f"powersensor_current_phase_{phase}"]
        assert current["unit"] == "A"
        assert current["device_class"] == "current"

