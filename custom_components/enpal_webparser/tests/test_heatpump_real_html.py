"""
Test parsing with real user-provided HTML containing Heatpump sensors.
"""
import pytest
from pathlib import Path

from custom_components.enpal_webparser.utils import parse_enpal_html_sensors, make_id
from custom_components.enpal_webparser.const import DEFAULT_GROUPS


def test_parse_real_heatpump_html():
    """Test parsing Heatpump sensors from real user HTML (deviceMessagesHP.html)."""
    
    # Read the real HTML file
    html_path = Path(__file__).parent / "fixtures" / "deviceMessagesHP.html"
    if not html_path.exists():
        pytest.skip(f"Test HTML file not found at {html_path}")
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Parse only Heatpump group
    sensors = parse_enpal_html_sensors(html_content, groups=["Heatpump"])
    
    # Verify we found sensors
    assert len(sensors) > 0, "Should find Heatpump sensors in the HTML"
    
    # Verify all sensors are in Heatpump group
    for sensor in sensors:
        assert sensor['group'] == 'Heatpump', f"Sensor {sensor['name']} should be in Heatpump group"
    
    # Check for expected sensors (note: no colon between group and sensor name)
    sensor_names = [s['name'] for s in sensors]
    
    assert "Heatpump DomesticHotWater Temperature" in sensor_names
    assert "Heatpump Energy Consumption Total Lifetime" in sensor_names
    assert "Heatpump Operation Mode Midea" in sensor_names
    assert "Heatpump Outside Temperature" in sensor_names
    assert "Heatpump Power Consumption Total" in sensor_names
    
    # Verify exactly 5 sensors
    assert len(sensors) == 5, f"Expected 5 Heatpump sensors, found {len(sensors)}"
    
    print(f"\n✓ Successfully parsed {len(sensors)} Heatpump sensors:")
    for sensor in sensors:
        print(f"  - {sensor['name']} = {sensor['value']}")


def test_heatpump_sensor_values():
    """Test that Heatpump sensor values are parsed correctly."""
    
    html_path = Path(__file__).parent / "fixtures" / "deviceMessagesHP.html"
    if not html_path.exists():
        pytest.skip(f"Test HTML file not found at {html_path}")
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    sensors = parse_enpal_html_sensors(html_content, groups=["Heatpump"])
    
    # Create a dict for easier lookup
    sensor_dict = {s['name']: s for s in sensors}
    
    # Check DomesticHotWater Temperature (value has encoding issue: 50\'b0C instead of 50°C)
    dhw_temp = sensor_dict.get("Heatpump DomesticHotWater Temperature")
    assert dhw_temp is not None
    # The value will have escaped backslash: 50\\'b0C
    assert "50" in str(dhw_temp['value']), \
        f"DomesticHotWater Temperature should contain '50': {dhw_temp['value']}"
    
    # Check Energy Consumption
    energy = sensor_dict.get("Heatpump Energy Consumption Total Lifetime")
    assert energy is not None
    assert "1333" in str(energy['value']), \
        f"Energy Consumption should contain '1333': {energy['value']}"
    
    # Check Operation Mode
    mode = sensor_dict.get("Heatpump Operation Mode Midea")
    assert mode is not None
    assert str(mode['value']) == "3", \
        f"Operation Mode should be '3': {mode['value']}"
    
    # Check Outside Temperature (value has encoding issue: 8\'b0C instead of 8°C)
    outside_temp = sensor_dict.get("Heatpump Outside Temperature")
    assert outside_temp is not None
    assert "8" in str(outside_temp['value']), \
        f"Outside Temperature should contain '8': {outside_temp['value']}"
    
    # Check Power Consumption
    power = sensor_dict.get("Heatpump Power Consumption Total")
    assert power is not None
    assert "0.01" in str(power['value']), \
        f"Power Consumption should contain '0.01': {power['value']}"
    
    print("\n✓ All Heatpump sensor values parsed correctly")


def test_heatpump_with_all_groups():
    """Test parsing Heatpump alongside other groups."""
    
    html_path = Path(__file__).parent / "fixtures" / "deviceMessagesHP.html"
    if not html_path.exists():
        pytest.skip(f"Test HTML file not found at {html_path}")
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Parse all groups
    sensors = parse_enpal_html_sensors(html_content, DEFAULT_GROUPS)
    
    # Count sensors by group
    groups = {}
    for sensor in sensors:
        group = sensor.get('group', 'Unknown')  # Handle sensors without group key
        if group:
            groups[group] = groups.get(group, 0) + 1
    
    # Verify Heatpump group exists and has 5 sensors
    assert 'Heatpump' in groups, "Heatpump group should be present"
    assert groups['Heatpump'] == 5, f"Heatpump should have 5 sensors, found {groups['Heatpump']}"
    
    # Verify other groups also exist
    assert 'Battery' in groups, "Battery group should be present"
    assert 'Inverter' in groups, "Inverter group should be present"
    assert 'PowerSensor' in groups, "PowerSensor group should be present"
    
    print(f"\n✓ Parsed {len(sensors)} total sensors across {len(groups)} groups:")
    for group, count in sorted(groups.items()):
        print(f"  - {group}: {count} sensors")


def test_heatpump_sensor_unique_ids():
    """Test that Heatpump sensors have correct unique IDs."""
    
    html_path = Path(__file__).parent / "fixtures" / "deviceMessagesHP.html"
    if not html_path.exists():
        pytest.skip(f"Test HTML file not found at {html_path}")
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    sensors = parse_enpal_html_sensors(html_content, groups=["Heatpump"])
    
    # Expected unique IDs based on sensor names
    expected_ids = [
        "heatpump_domestichotwater_temperature",
        "heatpump_energy_consumption_total_lifetime",
        "heatpump_operation_mode_midea",
        "heatpump_outside_temperature",
        "heatpump_power_consumption_total",
    ]
    
    # Generate unique IDs from sensor names
    actual_ids = [make_id(s['name']) for s in sensors]
    
    # Verify all expected IDs are present
    for expected_id in expected_ids:
        assert expected_id in actual_ids, f"Expected sensor ID '{expected_id}' not found"
    
    print("\n✓ All Heatpump sensor unique IDs are correct:")
    for sensor_id in sorted(actual_ids):
        print(f"  - {sensor_id}")


if __name__ == "__main__":
    # Run tests directly
    print("=" * 80)
    print("Testing Heatpump sensors with real user HTML")
    print("=" * 80)
    
    try:
        test_parse_real_heatpump_html()
        test_heatpump_sensor_values()
        test_heatpump_with_all_groups()
        test_heatpump_sensor_unique_ids()
        print("\n" + "=" * 80)
        print("All real Heatpump HTML tests PASSED ✓")
        print("=" * 80)
    except AssertionError as e:
        print(f"\n✗ Test FAILED: {e}")
        import sys
        sys.exit(1)
