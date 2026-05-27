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
from .const import ICON_MAP, STATE_CLASS_OVERRIDES

import re


def _display_name(name: str, group: str) -> str:
    """Build a consistent display name with 'Group: Label' format.

    The internal *name* (used for unique_id generation) sometimes already
    contains the group word embedded (e.g. 'Current Wallbox Connector 1
    Phase (B)').  For display purposes we always want the canonical form
    'Wallbox: Current Connector 1 Phase (B)'.
    """
    group_lower = group.lower()

    # Already has a proper 'Group: ...' prefix → keep as-is
    if name.lower().startswith(group_lower + ":"):
        return name

    # Remove the embedded group word (case-insensitive, whole word)
    pattern = re.compile(r'\b' + re.escape(group) + r'\b', re.IGNORECASE)
    label = pattern.sub('', name).strip()
    # Collapse any double spaces left behind
    label = re.sub(r' {2,}', ' ', label).strip(': ')

    return f"{group}: {label}" if label else name


class EnpalBaseSensor(CoordinatorEntity, SensorEntity):
    """Generic Enpal sensor entity using the update coordinator."""

    def __init__(self, sensor: dict, coordinator: DataUpdateCoordinator):
        super().__init__(coordinator)
        self._sensor = sensor
        raw_name = sensor.get("name", "unknown")
        group = sensor.get("group", "")
        self._attr_name = _display_name(raw_name, group) if group else raw_name
        self._attr_unique_id = make_id(raw_name)  # ID stays based on original name
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
        
        # allow explicit state_class from sensor dict
        self._attr_state_class = self._sensor.get("state_class")

        # measurement state class for numeric sensors if not explicitly set
        numeric_device_classes = {
            "power", "voltage", "current", "temperature", "frequency",
            "battery", "humidity", "pressure"
        }
        if self._attr_state_class is None:
            if device_class in numeric_device_classes or self._attr_native_unit_of_measurement in {"W","kW","V","A","Hz","°C","%"}:
                self._attr_state_class = "measurement"

        # custom overrides for state class if specified
        sensor_id = self._attr_unique_id
        if sensor_id in STATE_CLASS_OVERRIDES:
            self._attr_state_class = STATE_CLASS_OVERRIDES[sensor_id]

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


# Wallbox sensors whose value must be forced to 0 when not actively charging.
# Works around an Enpal firmware bug where these values freeze after charging ends.
_WALLBOX_ZERO_OVERRIDE_IDS = {
    "power_wallbox_connector_1_charging",
    "current_wallbox_connector_1_phase_a",
    "current_wallbox_connector_1_phase_b",
    "current_wallbox_connector_1_phase_c",
}


def build_sensor_entity(
    sensor: dict,
    coordinator: DataUpdateCoordinator,
    use_wallbox: bool = False,
) -> SensorEntity:
    """
    Factory function: Builds the appropriate sensor entity.
    Extendable for special cases or subclasses.
    """
    if sensor.get("device_class") == "energy":
        return EnpalEnergySensor(sensor, coordinator)
    if use_wallbox and make_id(sensor.get("name", "")) in _WALLBOX_ZERO_OVERRIDE_IDS:
        return EnpalWallboxPowerSensor(sensor, coordinator)
    return EnpalBaseSensor(sensor, coordinator)


class EnpalWallboxPowerSensor(EnpalBaseSensor):
    """Wallbox power/current sensor that reports 0 when not charging.

    Works around an Enpal firmware bug where power and current values
    freeze at their last reading after a charging session ends.
    """

    _WALLBOX_STATUS_ENTITY = "sensor.wallbox_status"

    @property
    def native_value(self):
        raw = self._sensor.get("value")
        status_state = self.hass.states.get(self._WALLBOX_STATUS_ENTITY)
        if status_state is not None and status_state.state != "charging":
            return 0
        return raw

    @property
    def extra_state_attributes(self):
        attrs = super().extra_state_attributes
        status_state = self.hass.states.get(self._WALLBOX_STATUS_ENTITY)
        if status_state is not None and status_state.state != "charging":
            attrs["enpal_raw_value"] = self._sensor.get("value")
            attrs["enpal_zero_reason"] = "wallbox not charging"
        return attrs


class EnpalEnergySensor(EnpalBaseSensor):
    def __init__(self, sensor: dict, coordinator: DataUpdateCoordinator):
        super().__init__(sensor, coordinator)
        # Default: Energy counter is total_increasing
        self._attr_state_class = "total_increasing"
        # Allow explicit overrides
        sensor_id = self._attr_unique_id
        if sensor_id in STATE_CLASS_OVERRIDES:
            self._attr_state_class = STATE_CLASS_OVERRIDES[sensor_id]
