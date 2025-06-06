#
# Tests for Enpal Webparser - utils.py
#
# Unit tests for utility functions used in the Enpal Webparser integration.
# Covers ID generation, value parsing, unit normalization, and device class detection.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
#
# To run: pytest custom_components/enpal_webparser/tests/test_utils.py
#

from custom_components.enpal_webparser.utils import (
    make_id,
    get_numeric_value,
    get_class_and_unit,
    normalize_value_and_unit,
    parse_enpal_html_sensors
)
from custom_components.enpal_webparser.const import UNIT_DEVICE_CLASS_MAP, DEFAULT_UNITS


def load_html_fixture(name):
    import os
    base = os.path.dirname(__file__)
    with open(os.path.join(base, "fixtures", name), "r", encoding="utf-8") as f:
        return f.read()

def test_make_id():
    """Test that make_id generates valid Home Assistant-style unique IDs from various strings."""
    assert make_id("Hallo Welt") == "hallo_welt"
    assert make_id("  Mehr_Fach  Test123") == "mehr_fach_test123"
    assert make_id("A-B-C") == "a_b_c"

def test_get_numeric_value():
    """Test that get_numeric_value extracts the numeric part from strings with various formats."""
    assert get_numeric_value("42,5 kWh") == "42.5"
    assert get_numeric_value("7.89A") == "7.89"
    assert get_numeric_value("n/a") == "n/a"

def test_get_class_and_unit():
    """Test that get_class_and_unit correctly detects the unit and device class from value strings."""
    unit, device_class = get_class_and_unit("1234 kWh", UNIT_DEVICE_CLASS_MAP)
    assert unit == "kWh"
    assert device_class == "energy"
    unit, device_class = get_class_and_unit("5.5 V", UNIT_DEVICE_CLASS_MAP)
    assert unit == "V"
    assert device_class == "voltage"
    unit, device_class = get_class_and_unit("17 bananas", UNIT_DEVICE_CLASS_MAP)
    assert unit is None
    assert device_class is None

def test_normalize_value_and_unit():
    """Test that normalize_value_and_unit converts Wh to kWh, handles default units, and leaves correct values."""
    value, unit = normalize_value_and_unit("1200 Wh", "Wh", "energy", DEFAULT_UNITS)
    assert value == "1.2"
    assert unit == "kWh"
    value, unit = normalize_value_and_unit("3.7 V", "V", "voltage", DEFAULT_UNITS)
    assert value == "3.7"
    assert unit == "V"
    value, unit = normalize_value_and_unit("99", None, "power", DEFAULT_UNITS)
    assert unit == "W"

def test_parse_enpal_html_sensors_basic():
    """Test parsing a basic Enpal HTML card and extracting the sensor dict with correct fields."""
    html = '''
    <div class="card">
        <h2>Inverter</h2>
        <table>
            <tr><th>Name</th><th>Value</th><th>Timestamp</th></tr>
            <tr><td>Energy total</td><td>1234 kWh</td><td>06/05/2025 10:12:01</td></tr>
        </table>
    </div>
    '''
    result = parse_enpal_html_sensors(html, groups=["Inverter"])
    assert len(result) == 1
    sensor = result[0]
    assert sensor["name"].startswith("Inverter")
    assert sensor["value"] == "1234"
    assert sensor["unit"] == "kWh"
    assert sensor["device_class"] == "energy"
    assert sensor["enpal_last_update"].startswith("2025-06-05T10:12:01")

def test_parse_enpal_html_sensors_ignore_wrong_group():
    """Test that sensors from non-matching groups are ignored during parsing."""
    html = '''
    <div class="card">
        <h2>Battery</h2>
        <table>
            <tr><th>Name</th><th>Value</th></tr>
            <tr><td>Charge</td><td>98 %</td></tr>
        </table>
    </div>
    '''
    result = parse_enpal_html_sensors(html, groups=["Inverter"])
    assert result == []


def test_parse_full_enpal_html():
    html = load_html_fixture("deviceMessages.html")
    sensors = parse_enpal_html_sensors(html, groups=["Inverter", "Battery", "Wallbox"])
    assert len(sensors) > 0
    # ... 
