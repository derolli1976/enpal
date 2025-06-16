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
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .utils import make_id
from .const import ICON_MAP


class EnpalBaseSensor(CoordinatorEntity, SensorEntity):
    """Generic Enpal sensor entity using the update coordinator."""

    def __init__(self, sensor: dict, coordinator: DataUpdateCoordinator):
        super().__init__(coordinator)
        self._sensor = sensor
        self._attr_name = sensor.get("name")
        self._attr_unique_id = make_id(sensor.get("name", "unknown"))
        self._attr_native_unit_of_measurement = sensor.get("unit")
        self._attr_enabled_default = sensor.get("enabled", True)

        icon_key = make_id(sensor.get("name", ""))
        if icon_key in ICON_MAP:
            self._attr_icon = ICON_MAP[icon_key]


        device_class = sensor.get("device_class")
        if device_class and hasattr(SensorDeviceClass, device_class.upper()):
            self._attr_device_class = getattr(SensorDeviceClass, device_class.upper())
        else:
            self._attr_device_class = device_class

    @property
    def native_value(self):
        return self._sensor.get("value")

    @property
    def extra_state_attributes(self):
        return {
            "enpal_last_update": self._sensor.get("enpal_last_update")
        }

    @cached_property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {("enpal_webparser", "enpal_device")},
            "name": "Enpal Webgerät",
            "manufacturer": "Enpal",
            "model": "Webparser",
        }

    def _handle_coordinator_update(self):
        for s in self.coordinator.data:
            if make_id(s.get("name", "")) == self._attr_unique_id:
                self._sensor = s
                break
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._handle_coordinator_update()


def build_sensor_entity(sensor: dict, coordinator: DataUpdateCoordinator) -> SensorEntity:
    """
    Factory function: Builds the appropriate sensor entity.
    Extendable for special cases or subclasses.
    """
    if sensor.get("device_class") == "energy":
        return EnpalEnergySensor(sensor, coordinator)
    return EnpalBaseSensor(sensor, coordinator)


class EnpalEnergySensor(EnpalBaseSensor):
    def __init__(self, sensor: dict, coordinator: DataUpdateCoordinator):
        super().__init__(sensor, coordinator)
        self._attr_state_class = "total_increasing"
