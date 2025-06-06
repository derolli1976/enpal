#
# Tests for Enpal Webparser - entity_factory.py
#
# Unit tests for the entity factory logic and base/specialized sensor entity classes.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
#
# To run: pytest custom_components/enpal_webparser/tests/test_entity_factory.py
#

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from custom_components.enpal_webparser.entity_factory import (
    build_sensor_entity,
    EnpalBaseSensor,
    EnpalEnergySensor,
)

class DummyCoordinator(DataUpdateCoordinator):
    # Minimal dummy for testing, no real update logic needed.
    def __init__(self):
        pass


def test_base_sensor_creation():
    """Test that a base sensor entity is correctly created from a standard sensor dict."""
    sensor_dict = {
        "name": "Test Sensor",
        "value": "42.1",
        "unit": "V",
        "device_class": "voltage",
        "enabled": True,
        "enpal_last_update": "2024-06-07T09:13:00",
    }
    sensor = build_sensor_entity(sensor_dict, DummyCoordinator())
    assert isinstance(sensor, EnpalBaseSensor)
    assert sensor.name == "Test Sensor"
    assert sensor.native_value == "42.1"
    assert sensor.native_unit_of_measurement == "V"
    assert sensor.device_class == "voltage" or getattr(sensor.device_class, 'value', None) == "voltage"
    assert sensor.extra_state_attributes is not None
    assert sensor.extra_state_attributes["enpal_last_update"] == "2024-06-07T09:13:00"

def test_energy_sensor_creation():
    """Test that the factory returns a specialized EnpalEnergySensor for device_class 'energy'."""
    sensor_dict = {
        "name": "Test Energy",
        "value": "12.3",
        "unit": "kWh",
        "device_class": "energy",
        "enabled": True,
        "enpal_last_update": None,
    }
    sensor = build_sensor_entity(sensor_dict, DummyCoordinator())
    assert isinstance(sensor, EnpalEnergySensor)
    assert getattr(sensor, "state_class", None) == "total_increasing"

def test_sensor_unique_id():
    """Test that the entity unique_id is generated from the sensor name."""
    sensor_dict = {
        "name": "Test Sensor 1",
        "value": "10",
    }
    sensor = build_sensor_entity(sensor_dict, DummyCoordinator())
    assert sensor.unique_id is not None
    assert "test_sensor_1" in sensor.unique_id

def test_sensor_device_info():
    """Test that the entity device_info dict is set with the expected keys and values."""
    sensor_dict = {
        "name": "Device Info Sensor",
        "value": "5",
    }
    sensor = build_sensor_entity(sensor_dict, DummyCoordinator())
    device_info = sensor.device_info
    assert device_info is not None
    assert device_info.get("identifiers") == {("enpal_webparser", "enpal_device")}
    assert device_info.get("manufacturer") == "Enpal"
    assert device_info.get("model") == "Webparser"

