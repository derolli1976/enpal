# pyright: reportIncompatibleVariableOverride=false
#
# Home Assistant Custom Component: Enpal Webparser
#
# File: sensor.py
#
# Description:
#   Home Assistant sensor platform for Enpal solar installations.
#   Parses data from the local Enpal HTML site and provides it as sensors.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
# Repository:   https://github.com/derolli1976/enpal
#
# Compatible with Home Assistant Core 2024.x and later.
#
# See README.md for setup and usage instructions.
#

from datetime import datetime, timedelta
from functools import cached_property
import logging

from bs4 import BeautifulSoup

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .entity_factory import build_sensor_entity

from .wallbox_api import WallboxApiClient
from .utils import (
    make_id,
    parse_enpal_html_sensors
)

from .const import (
    DEFAULT_INTERVAL,
    DEFAULT_URL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    _LOGGER.info("[Enpal] sensor.py async_setup_entry started")

    url = entry.options.get("url", DEFAULT_URL)
    interval = entry.options.get("interval", DEFAULT_INTERVAL)
    groups = entry.options.get("groups", [])
    _LOGGER.debug("[Enpal] Configuration - URL: %s, Interval: %s, Groups: %s", url, interval, groups)

    last_successful_data = []

    async def async_update_data():
        nonlocal last_successful_data
        try:
            session = async_get_clientsession(hass)
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    raise Exception(f"Unexpected status code: {resp.status}")
                html = await resp.text()

            _LOGGER.debug("[Enpal] HTML content fetched successfully from %s", url)
            soup = BeautifulSoup(html, 'html.parser')
            cards = soup.find_all("div", class_="card")
            _LOGGER.debug("[Enpal] Found %d card(s) in HTML", len(cards))

            sensors = parse_enpal_html_sensors(html, groups)
            
            return sensors

        except Exception as e:
            if last_successful_data:
                _LOGGER.warning("[Enpal] Error during update, using last known good values: %s", e)
                return last_successful_data
            else:
                _LOGGER.exception("[Enpal] No previous data available")
                raise UpdateFailed(f"Initial data fetch failed: {e}")

    coordinator = DataUpdateCoordinator(
        hass,
        logger=_LOGGER,
        name="Enpal Webparser",
        update_method=async_update_data,
        update_interval=timedelta(seconds=interval),
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("cumulative_energy_state", {
        "value": 0.0,
        "last_updated": datetime.now().isoformat()
    })

    hass.data[DOMAIN]["coordinator"] = coordinator

    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info("[Enpal] Verfügbare Sensoren nach HTML-Parsing:")
    for sensor in coordinator.data:
        _LOGGER.info("[Enpal]   Name: %s -> UID: %s", sensor["name"], make_id(sensor["name"]))

    entities = []
    for sensor_dict in coordinator.data:
        _LOGGER.debug("[Enpal] Adding sensor entity: %s", sensor_dict["name"])
        entities.append(build_sensor_entity(sensor_dict, coordinator))


    entities.append(CumulativeEnergySensor(hass, coordinator, "Inverter Power DC Total (Huawei)", interval))
    entities.append(DailyResetFromEntitySensor(hass, "sensor.inverter_energy_produced_total_dc"))

    if entry.options.get("use_wallbox_addon", False):
        _LOGGER.info("[Enpal] Wallbox add-on enabled, setting up coordinator")

        api_client = WallboxApiClient(hass)
        wallbox_data = {}

        async def async_wallbox_update():
            nonlocal wallbox_data
            try:
                data = await api_client.get_status()
                if data is None:
                    raise Exception("Wallbox API returned None")
                
                _LOGGER.debug("[Enpal] Wallbox status data: %s", data)
                wallbox_data = data
                return data
            except Exception as e:
                if wallbox_data:
                    _LOGGER.warning("[Enpal] Wallbox update failed - using last known data: %s", e)
                    return wallbox_data
                else:
                    _LOGGER.warning("[Enpal] Wallbox update failed - no previous data yet: %s", e)
                    raise UpdateFailed(f"Wallbox update failed and no previous data: {e}")

        wallbox_coordinator = DataUpdateCoordinator(
            hass,
            logger=_LOGGER,
            name="Wallbox Status",
            update_method=async_wallbox_update,
            update_interval=timedelta(seconds=interval),
        )

        hass.async_create_task(wallbox_coordinator.async_refresh())

        entities.extend([
            WallboxModeSensor(wallbox_coordinator),
            WallboxStatusSensor(wallbox_coordinator),
        ])
        _LOGGER.debug("[Enpal] Wallbox-Sensoren hinzugefügt")

    async_add_entities(entities)


class CumulativeEnergySensor(SensorEntity, RestoreEntity):  
    def __init__(self, hass: HomeAssistant, coordinator: DataUpdateCoordinator, sensor_name: str, interval_seconds: int):
        self.hass = hass
        self._attr_name = str("Inverter: Energy produced total (DC)")
        self._attr_unique_id = str("cumulative_energy_produced_dc_kwh")
        self._attr_device_class = SensorDeviceClass.ENERGY   
        self._attr_state_class = "total_increasing"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_icon = "mdi:solar-power"
        self._coordinator = coordinator
        self._source_uid = make_id(sensor_name)
        self._interval_hours = interval_seconds / 3600
        self._state = self.hass.data[DOMAIN]["cumulative_energy_state"]
        self._value = None
        self._last_updated = None

    @property
    def native_value(self) -> StateType:
        return round(self._value or 0.0, 3)

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "last_updated": self._last_updated
        }

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, 'unknown', 'unavailable'):
            try:
                self._value = float(last_state.state)
                _LOGGER.info("[Enpal] Recovered Energy Value: %.3f kWh", self._value)
            except ValueError:
                self._value = 0.0
        else:
            self._value = 0.0
        self._coordinator.async_add_listener(self._handle_coordinator_update)

    def _handle_coordinator_update(self):
        for sensor in self._coordinator.data:
            _LOGGER.debug("[Enpal] Checking Sensor: %s (%s)", sensor["name"], make_id(sensor["name"]))
            if make_id(sensor["name"]) == self._source_uid:
                try:
                    power_watt = float(sensor["value"])
                    energy_kwh = power_watt * self._interval_hours / 1000
                    if self._value is None:
                        self._value = 0.0
                    self._value += energy_kwh
                    self._last_updated = datetime.now().isoformat()
                    _LOGGER.debug("[Enpal] +%.5f kWh -> Total: %.3f", energy_kwh, self._state["value"])
                except Exception as e:
                    _LOGGER.warning("[Enpal] Error in energy calculation: %s", e)
                break
        self.async_write_ha_state()

    @cached_property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "enpal_device")},
            name="Enpal Webgerät",
            manufacturer="Enpal",
            model="Webparser",
        )

class DailyResetFromEntitySensor(SensorEntity, RestoreEntity):  
    def __init__(self, hass: HomeAssistant, source_entity_id: str):
        self.hass = hass
        self._attr_name = str("Inverter: Energy produced today (DC)")
        self._attr_unique_id = str("daily_energy_produced_dc_kwh")
        self._attr_device_class = SensorDeviceClass.ENERGY 
        self._attr_state_class = "total"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_icon = "mdi:calendar-refresh"
        self._source_entity_id = source_entity_id
        self._today_start_value = None
        self._value = 0.0
        self._last_reset = datetime.now().date()

    @property
    def native_value(self) -> StateType:
        return round(self._value or 0.0, 3)

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "last_reset": self._last_reset.isoformat(),
            "start_value": self._today_start_value if self._today_start_value is not None else "Not set"
        }

    async def async_added_to_hass(self):
        await RestoreEntity.async_added_to_hass(self)
        async_track_state_change_event(
            self.hass, self._source_entity_id, self._handle_state_update
        )
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, 'unknown', 'unavailable'):
            try:
                self._value = float(last_state.state)
                self._today_start_value = self._try_float(last_state.attributes.get("start_value"))
                last_reset_str = last_state.attributes.get("last_reset")
                if last_reset_str:
                    self._last_reset = datetime.fromisoformat(last_reset_str).date()
            except Exception:
                pass

    @staticmethod
    def _try_float(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    @callback
    def _handle_state_update(self, event):
        today = datetime.now().date()
        try:
            new_total = float(event.data["new_state"].state)
        except (TypeError, ValueError):
            return

        if self._today_start_value is None or self._last_reset != today:
            self._today_start_value = new_total
            self._last_reset = today
            self._value = 0.0
        else:
            self._value = max(new_total - self._today_start_value, 0)

        self.async_schedule_update_ha_state()

    @cached_property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "enpal_device")},
            name="Enpal Webgerät",
            manufacturer="Enpal",
            model="Webparser",
        )


class WallboxCoordinatorEntity(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, name, unique_id, key):
        super().__init__(coordinator)
        self._attr_name = str(name)
        self._attr_unique_id = str(unique_id)
        self._key = key
        self._attr_icon = "mdi:ev-station"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @cached_property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "enpal_device")},
            name="Enpal Webgerät",
            manufacturer="Enpal",
            model="Webparser",
        )

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data:
            return self.coordinator.data.get(self._key)
        return None

class WallboxModeSensor(WallboxCoordinatorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Wallbox Lademodus", "wallbox_mode", "mode")

class WallboxStatusSensor(WallboxCoordinatorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Wallbox Status", "wallbox_status", "status")
