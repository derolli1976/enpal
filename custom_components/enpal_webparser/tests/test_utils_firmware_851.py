"""Parsing of the deviceMessages page as rendered by Enpal firmware 8.51.

Firmware 8.51 added a "Notes" column to every sensor table and renamed several
inverter data points (see issue #148).
"""

from custom_components.enpal_webparser.utils import make_id, parse_enpal_html_sensors

GROUPS = ["Site Data", "IoTEdgeDevice", "Inverter", "Battery", "PowerSensor", "Wallbox"]


def _by_id(sensors):
    return {make_id(s["name"]): s for s in sensors}


def test_note_rows_are_not_parsed_as_values(real_html_851):
    sensors = parse_enpal_html_sensors(real_html_851, groups=GROUPS)

    assert sensors
    for sensor in sensors:
        value = sensor["value"]
        assert not value.startswith("missing:")
        assert not value.startswith("invalid:")
        assert "ProcessImageValueKey" not in value


def test_sensor_without_value_is_omitted(real_html_851):
    """Cpu.Load only has a validation note, so no sensor must be produced."""
    sensors = parse_enpal_html_sensors(real_html_851, groups=GROUPS)

    assert "iotedgedevice_cpu_load" not in _by_id(sensors)
    assert "iotedgedevice_memory_usage" not in _by_id(sensors)


def test_values_and_units_are_still_parsed(real_html_851):
    sensors = _by_id(parse_enpal_html_sensors(real_html_851, groups=GROUPS))

    power_dc = sensors["inverter_power_dc_total"]
    assert power_dc["value"] == "4966"
    assert power_dc["unit"] == "W"
    assert power_dc["device_class"] == "power"

    # Wh is still normalized to kWh with the extra Notes column present.
    charged = sensors["energy_wallbox_connector_1_charged_total"]
    assert charged["value"] == "12642.33"
    assert charged["unit"] == "kWh"


def test_renamed_inverter_keys_keep_their_legacy_ids(real_html_851):
    sensors = _by_id(parse_enpal_html_sensors(real_html_851, groups=["Inverter"]))

    # Power.AC.Phase.A.Inverter must not create a second entity.
    assert "inverter_power_ac_phase_a" in sensors
    assert "power_ac_phase_a_inverter" not in sensors
    assert sensors["inverter_power_ac_phase_a"]["value"] == "-3094"

    assert "inverter_energy_battery_charge_day" in sensors
    assert "inverter_power_battery_charge_discharge" in sensors


def test_wallbox_status_source_is_still_detected(real_html_851):
    sensors = _by_id(parse_enpal_html_sensors(real_html_851, groups=["Wallbox"]))

    assert sensors["status_wallbox_connector_1"]["value"] == "Preparing"
    assert sensors["wallbox_mode_charge_connector_1"]["value"] == "Fast"
