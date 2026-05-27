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

import pytest
from datetime import timedelta

from unittest.mock import AsyncMock

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from custom_components.enpal_webparser.entity_factory import (
    build_sensor_entity,
    EnpalBaseSensor,
    EnpalEnergySensor,
    EnpalWallboxPowerSensor,
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

@pytest.fixture
def hass():
    """Return a mocked hass instance."""
    hass = AsyncMock(spec=HomeAssistant)
    return hass

@pytest.fixture
def mock_sensor_dict():
    return {
        "name": "Test Sensor",
        "value": 123.45,
        "unit": "kWh",
        "device_class": "energy",
        "enpal_last_update": "2024-06-01T12:00:00",
    }

@pytest.fixture
def hass_coordinator():
    return DummyCoordinator()

@pytest.mark.asyncio
async def test_build_energy_sensor_full(hass: HomeAssistant, mock_sensor_dict, hass_coordinator):
    sensor = build_sensor_entity(mock_sensor_dict, hass_coordinator)
    assert isinstance(sensor, EnpalEnergySensor)
    assert sensor.name == "Test Sensor"
    assert sensor.native_value == 123.45
    assert sensor.native_unit_of_measurement == "kWh"
    assert sensor.device_class == "energy"
    assert sensor.state_class == "total_increasing"
    assert "enpal_last_update" in sensor.extra_state_attributes


# ---------- Wallbox power zero-override tests ----------

class _FakeState:
    """Minimal stand-in for homeassistant.core.State."""
    def __init__(self, state: str):
        self.state = state


class _FakeHass:
    """Minimal hass stub with a states registry."""
    def __init__(self, states_map: dict):
        self._map = states_map

    class _States:
        def __init__(self, m):
            self._m = m
        def get(self, entity_id):
            return self._m.get(entity_id)

    @property
    def states(self):
        return self._States(self._map)


def _wallbox_power_sensor(status_state: str | None):
    """Create an EnpalWallboxPowerSensor with a faked wallbox status."""
    sensor_dict = {
        "name": "Power Wallbox Connector 1 Charging",
        "value": "4500",
        "unit": "W",
        "device_class": "power",
        "enabled": True,
        "group": "Wallbox",
    }
    entity = build_sensor_entity(sensor_dict, DummyCoordinator(), use_wallbox=True)
    assert isinstance(entity, EnpalWallboxPowerSensor)

    if status_state is not None:
        entity.hass = _FakeHass({"sensor.wallbox_status": _FakeState(status_state)})
    else:
        entity.hass = _FakeHass({})
    return entity


def test_wallbox_power_zero_when_not_charging():
    """Power sensor returns 0 when wallbox status is not 'charging'."""
    entity = _wallbox_power_sensor("connected")
    assert entity.native_value == 0
    assert entity.extra_state_attributes.get("enpal_raw_value") == "4500"
    assert entity.extra_state_attributes.get("enpal_zero_reason") == "wallbox not charging"


def test_wallbox_power_passthrough_when_charging():
    """Power sensor returns raw value when wallbox status is 'charging'."""
    entity = _wallbox_power_sensor("charging")
    assert entity.native_value == "4500"
    assert "enpal_raw_value" not in entity.extra_state_attributes


def test_wallbox_power_passthrough_when_status_missing():
    """Power sensor returns raw value when wallbox_status entity doesn't exist."""
    entity = _wallbox_power_sensor(None)
    assert entity.native_value == "4500"
    assert "enpal_raw_value" not in entity.extra_state_attributes


def test_wallbox_current_sensor_zero_override():
    """Current sensor also gets zero-override treatment."""
    sensor_dict = {
        "name": "Current Wallbox Connector 1 Phase (A)",
        "value": "12.31",
        "unit": "A",
        "device_class": "current",
        "enabled": True,
        "group": "Wallbox",
    }
    entity = build_sensor_entity(sensor_dict, DummyCoordinator(), use_wallbox=True)
    assert isinstance(entity, EnpalWallboxPowerSensor)
    entity.hass = _FakeHass({"sensor.wallbox_status": _FakeState("connected")})
    assert entity.native_value == 0


def test_wallbox_power_not_used_without_flag():
    """Without use_wallbox=True, the regular base sensor is returned."""
    sensor_dict = {
        "name": "Power Wallbox Connector 1 Charging",
        "value": "4500",
        "unit": "W",
        "device_class": "power",
    }
    entity = build_sensor_entity(sensor_dict, DummyCoordinator(), use_wallbox=False)
    assert isinstance(entity, EnpalBaseSensor)
    assert not isinstance(entity, EnpalWallboxPowerSensor)


