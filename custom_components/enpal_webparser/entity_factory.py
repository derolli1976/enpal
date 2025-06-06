#
# Home Assistant Custom Component: Enpal Webparser
#
# File: entity_factory.py
#
# Description:
#   Entity factory and base classes for Enpal Webparser sensors.
#   Provides a flexible, testable way to create Home Assistant SensorEntity objects
#   from parsed sensor data dictionaries.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
# Repository:   https://github.com/derolli1976/enpal
#
# Compatible with Home Assistant Core 2024.x and later.
#
# See README.md for setup and usage instructions.
#

from functools import cached_property
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.entity import DeviceInfo

from .utils import make_id

class EnpalBaseSensor(SensorEntity):
    """Generische Enpal Sensor-Entity, geeignet für die meisten Sensoren."""

    def __init__(self, sensor: dict, coordinator: DataUpdateCoordinator):
        self._attr_name = sensor.get("name")
        self._attr_unique_id = make_id(sensor.get("name", "unknown"))
        self._attr_native_value = sensor.get("value")
        self._attr_native_unit_of_measurement = sensor.get("unit")
        # device_class als Enum, falls möglich:
        device_class = sensor.get("device_class")
        if device_class and hasattr(SensorDeviceClass, device_class.upper()):
            self._attr_device_class = getattr(SensorDeviceClass, device_class.upper())
        else:
            self._attr_device_class = device_class
        self._attr_enabled_default = sensor.get("enabled", True)
        self._attr_extra_state_attributes = {
            "enpal_last_update": sensor.get("enpal_last_update")
        }
        self._coordinator = coordinator

    @cached_property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {("enpal_webparser", "enpal_device")},
            "name": "Enpal Webgerät",
            "manufacturer": "Enpal",
            "model": "Webparser",
        }


    async def async_update(self):
        await self._coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        self._coordinator.async_add_listener(self._handle_coordinator_update)

    def _handle_coordinator_update(self):
        # Hier kannst du das Update-Handling noch anpassen, falls nötig!
        self.async_write_ha_state()

def build_sensor_entity(sensor: dict, coordinator: DataUpdateCoordinator) -> SensorEntity:
    """
    Factory-Funktion: Baut die passende SensorEntity.
    Hier kannst du auch Spezialfälle oder Subklassen einbauen.
    """
    # Beispiel für Spezialfall: Energiesensor mit zusätzlichem Attribut
    if sensor.get("device_class") == "energy":
        return EnpalEnergySensor(sensor, coordinator)
    # Weitere Spezialfälle ...
    return EnpalBaseSensor(sensor, coordinator)

# Beispiel für einen spezialisierten Sensor
class EnpalEnergySensor(EnpalBaseSensor):
    def __init__(self, sensor: dict, coordinator: DataUpdateCoordinator):
        super().__init__(sensor, coordinator)
        self._attr_state_class = "total_increasing"  # Nur für Energie!

    # Hier könntest du noch eigene Properties oder Methoden ergänzen
