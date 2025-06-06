from custom_components.enpal_webparser.utils import parse_enpal_html_sensors


def test_parse_real_html_sensor_count(real_html):
    sensors = parse_enpal_html_sensors(real_html, groups=['Site Data', 'IoTEdgeDevice', 'Inverter', 'Battery', 'PowerSensor', 'Wallbox'])
    assert isinstance(sensors, list)
    assert len(sensors) > 50  # Expecting a large number of sensors
    assert all("name" in s and "value" in s for s in sensors)

def test_extract_specific_sensor(real_html):
    sensors = parse_enpal_html_sensors(real_html, groups=["Wallbox"])
    names = [s["name"] for s in sensors]
    print(f"Found {len(names)} Wallbox sensors:")
    assert len(names) > 0  # Ensure we found some Wallbox sensors
       
    assert any("State Wallbox Connector 1 Charge" in n for n in names)
    assert any("Voltage Wallbox Connector 1 Phase (B)" in n for n in names)

def test_inverter_group_contains_voltage_sensors(real_html):
    sensors = parse_enpal_html_sensors(real_html, groups=["Inverter"])
    voltage_sensors = [s for s in sensors if "Voltage" in s["name"]]
    assert len(voltage_sensors) >= 3
    for vs in voltage_sensors:
        assert vs["unit"] in ["V"]
        assert vs["device_class"] == "voltage"

def test_all_sensors_have_valid_keys(real_html):
    sensors = parse_enpal_html_sensors(real_html, groups=['Site Data', 'IoTEdgeDevice', 'Inverter', 'Battery', 'PowerSensor', 'Wallbox'])
    for s in sensors:
        assert "name" in s
        assert "value" in s
        assert "unit" in s
        assert "device_class" in s
        assert "enabled" in s
        assert "enpal_last_update" in s