"""Test calculated current sensors for PowerSensor."""
import pytest
from custom_components.enpal_webparser.utils import add_calculated_current_sensors


def test_calculate_current_sensors():
    """Test that current is calculated correctly from power and voltage."""
    # Test data based on user's screenshot:
    # Phase A: -61W / 231.1V = -0.26A
    # Phase B: -19W / 230.1V = -0.08A
    # Phase C: 77W / 230.3V = 0.33A
    
    sensors = [
        {
            "name": "PowerSensor: Power AC Phase (A)",
            "value": "-61",
            "unit": "W",
            "group": "PowerSensor",
            "enabled": True,
            "enpal_last_update": "2025-10-31T09:57:14.635Z",
        },
        {
            "name": "PowerSensor: Voltage Phase (A)",
            "value": "231.1",
            "unit": "V",
            "group": "PowerSensor",
            "enabled": True,
            "enpal_last_update": "2025-10-31T09:57:14.634Z",
        },
        {
            "name": "PowerSensor: Power AC Phase (B)",
            "value": "-19",
            "unit": "W",
            "group": "PowerSensor",
            "enabled": True,
            "enpal_last_update": "2025-10-31T09:57:14.635Z",
        },
        {
            "name": "PowerSensor: Voltage Phase (B)",
            "value": "230.1",
            "unit": "V",
            "group": "PowerSensor",
            "enabled": True,
            "enpal_last_update": "2025-10-31T09:57:14.634Z",
        },
        {
            "name": "PowerSensor: Power AC Phase (C)",
            "value": "77",
            "unit": "W",
            "group": "PowerSensor",
            "enabled": True,
            "enpal_last_update": "2025-10-31T09:57:14.636Z",
        },
        {
            "name": "PowerSensor: Voltage Phase (C)",
            "value": "230.3",
            "unit": "V",
            "group": "PowerSensor",
            "enabled": True,
            "enpal_last_update": "2025-10-31T09:57:14.634Z",
        },
    ]
    
    result = add_calculated_current_sensors(sensors)
    
    # Should have original 6 sensors + 3 calculated current sensors
    assert len(result) == 9
    
    # Find calculated current sensors by name
    current_a = next((s for s in result if "Current Phase (A)" in s["name"]), None)
    current_b = next((s for s in result if "Current Phase (B)" in s["name"]), None)
    current_c = next((s for s in result if "Current Phase (C)" in s["name"]), None)
    
    assert current_a is not None, "Current sensor for phase A not found"
    assert current_b is not None, "Current sensor for phase B not found"
    assert current_c is not None, "Current sensor for phase C not found"
    
    # Check calculated values (I = P / U)
    # Phase A: -61 / 231.1 = -0.26A
    assert float(current_a["value"]) == pytest.approx(-0.26, abs=0.01)
    assert current_a["unit"] == "A"
    assert current_a["device_class"] == "current"
    assert current_a["group"] == "PowerSensor"
    
    # Phase B: -19 / 230.1 = -0.08A
    assert float(current_b["value"]) == pytest.approx(-0.08, abs=0.01)
    assert current_b["unit"] == "A"
    
    # Phase C: 77 / 230.3 = 0.33A
    assert float(current_c["value"]) == pytest.approx(0.33, abs=0.01)
    assert current_c["unit"] == "A"


def test_calculate_current_sensors_missing_voltage():
    """Test that calculation handles missing voltage gracefully."""
    sensors = [
        {
            "name": "PowerSensor: Power AC Phase (A)",
            "value": "-61",
            "unit": "W",
            "group": "PowerSensor",
            "enabled": True,
            "enpal_last_update": "2025-10-31T09:57:14.635Z",
        },
        # Missing voltage sensor for phase A
    ]
    
    result = add_calculated_current_sensors(sensors)
    
    # Should have only the original sensor (no current calculated)
    assert len(result) == 1
    assert "Power AC Phase (A)" in result[0]["name"]


def test_calculate_current_sensors_zero_voltage():
    """Test that calculation handles zero voltage (division by zero)."""
    sensors = [
        {
            "name": "PowerSensor: Power AC Phase (A)",
            "value": "-61",
            "unit": "W",
            "group": "PowerSensor",
            "enabled": True,
            "enpal_last_update": "2025-10-31T09:57:14.635Z",
        },
        {
            "name": "PowerSensor: Voltage Phase (A)",
            "value": "0",
            "unit": "V",
            "group": "PowerSensor",
            "enabled": True,
            "enpal_last_update": "2025-10-31T09:57:14.634Z",
        },
    ]
    
    result = add_calculated_current_sensors(sensors)
    
    # Should have only the original sensors (no current calculated due to zero voltage)
    assert len(result) == 2
    assert not any("Current Phase (A)" in s["name"] for s in result)


def test_calculate_current_sensors_non_powersensor_group():
    """Test that calculation only applies to PowerSensor group."""
    sensors = [
        {
            "name": "Inverter: Power AC Phase (A)",
            "value": "100",
            "unit": "W",
            "group": "Inverter",  # Not PowerSensor
            "enabled": True,
            "enpal_last_update": "2025-10-31T09:57:14.635Z",
        },
        {
            "name": "Inverter: Voltage Phase (A)",
            "value": "230",
            "unit": "V",
            "group": "Inverter",
            "enabled": True,
            "enpal_last_update": "2025-10-31T09:57:14.634Z",
        },
    ]
    
    result = add_calculated_current_sensors(sensors)
    
    # Should have only the original sensors (no calculation for non-PowerSensor group)
    assert len(result) == 2
    assert not any("Current Phase" in s["name"] for s in result)
