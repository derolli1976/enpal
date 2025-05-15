from datetime import datetime, timedelta
import asyncio
import logging
import re

import aiohttp
from bs4 import BeautifulSoup

from homeassistant.core import HomeAssistant, callback
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity, UpdateFailed
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_URL, DEFAULT_WALLBOX_API_ENDPOINT


_LOGGER = logging.getLogger(__name__)


def friendly_name(group: str, sensor: str) -> str:
    group_lower = group.lower()
    parts = sensor.split('.')
    label = []
    skip_next = False

    for i, part in enumerate(parts):
        if i + 1 < len(parts) and re.fullmatch(r"[A-Z]", parts[i + 1]):
            label.append(f"{part} ({parts[i + 1]})")
            skip_next = True
        elif skip_next:
            skip_next = False
        else:
            label.append(part)

    full_label = ' '.join(label)
    return full_label if group_lower in full_label.lower() else f"{group}: {full_label}"


def make_id(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^\w]+", "_", name)
    return name.strip("_")


def get_numeric_value(value: str):
    match = re.search(r"[-+]?[0-9]*\.?[0-9]+", value.replace(',', '.'))
    return match.group(0) if match else value


def get_class_and_unit(value: str):
    value = value.strip()
    unit_map = {
        "kWh": "energy",
        "Wh": "energy",
        "kW": "power",
        "W": "power",
        "V": "voltage",
        "A": "current",
        "Hz": "frequency",
        "°C": "temperature",
        "%": None
    }
    for unit, device_class in unit_map.items():
        if value.endswith(unit):
            return unit, device_class
    return None, None


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
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as resp:
                    if resp.status != 200:
                        raise Exception(f"Unexpected status code: {resp.status}")
                    html = await resp.text()

            _LOGGER.debug("[Enpal] HTML content fetched successfully from %s", url)
            soup = BeautifulSoup(html, 'html.parser')
            cards = soup.find_all("div", class_="card")
            _LOGGER.debug("[Enpal] Found %d card(s) in HTML", len(cards))

            sensors = []
            for card in cards:
                group = card.find("h2").text.strip()
                if group not in groups:
                    continue

                rows = card.find_all("tr")[1:]
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        raw_name = cols[0].text.strip()
                        value_raw = cols[1].text.strip()
                        value_clean = get_numeric_value(value_raw)
                        unit, device_class = get_class_and_unit(value_raw)

                        timestamp_str = cols[2].text.strip() if len(cols) > 2 else None
                        timestamp_iso = None
                        if timestamp_str:
                            try:
                                dt = datetime.strptime(timestamp_str, "%m/%d/%Y %H:%M:%S")
                                timestamp_iso = dt.isoformat()
                            except ValueError:
                                timestamp_iso = timestamp_str

                        if unit == "Wh":
                            try:
                                value_clean = str(round(float(value_clean) / 1000, 3))
                                unit = "kWh"
                            except ValueError:
                                _LOGGER.warning("[Enpal] Unable to convert Wh to kWh for value: %s", value_clean)

                        if device_class and unit is None:
                            default_units = {
                                "power": "W",
                                "energy": "kWh",
                                "voltage": "V",
                                "current": "A",
                                "temperature": "°C",
                                "frequency": "Hz",
                            }
                            unit = default_units.get(device_class)

                        sensor_data = {
                            "name": friendly_name(group, raw_name),
                            "value": value_clean,
                            "unit": unit,
                            "device_class": device_class,
                            "enabled": group in groups,
                            "enpal_last_update": timestamp_iso
                        }
                        sensors.append(sensor_data)

            _LOGGER.info("[Enpal] Loaded %d sensor(s) from HTML", len(sensors))
            last_successful_data = sensors
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
    for sensor in coordinator.data:
        uid = make_id(sensor["name"])
        _LOGGER.debug("[Enpal] Adding sensor entity: %s", sensor["name"])
        entities.append(EnpalSensor(uid, sensor, coordinator))

    entities.append(CumulativeEnergySensor(hass, coordinator, "Inverter Power DC Total (Huawei)", interval))
    entities.append(DailyResetFromEntitySensor(hass, "sensor.inverter_energy_produced_total_dc"))



    if entry.options.get("use_wallbox_addon", False):
        wallbox_url = f"{DEFAULT_WALLBOX_API_ENDPOINT}/status"
        _LOGGER.info("[Enpal] Wallbox add-on enabled, URL: %s", wallbox_url)

        wallbox_data = {}

        async def async_wallbox_update():
            nonlocal wallbox_data
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(wallbox_url, timeout=10) as resp:
                        if resp.status != 200:
                            raise Exception(f"Wallbox API Error: {resp.status}")
                        data = await resp.json()
                        _LOGGER.debug("[Enpal] Wallbox status data: %s", data)
                        wallbox_data = data
                        return data
            except Exception as e:
                if wallbox_data:
                    _LOGGER.warning("[Enpal] Wallbox update failed – using last known data: %s", e)
                    return wallbox_data
                else:
                    _LOGGER.warning("[Enpal] Wallbox update failed – no previous data yet: %s", e)
                    raise UpdateFailed(f"Wallbox update failed and no previous data: {e}")

        wallbox_coordinator = DataUpdateCoordinator(
            hass,
            logger=_LOGGER,
            name="Wallbox Status",
            update_method=async_wallbox_update,
            update_interval=timedelta(seconds=interval),
        )

        # KEIN await – Hintergrund-Task starten, damit Home Assistant nicht crasht
        hass.async_create_task(wallbox_coordinator.async_refresh())

        entities.extend([
            WallboxModeSensor(wallbox_coordinator),
            WallboxStatusSensor(wallbox_coordinator),
        ])
        _LOGGER.debug("[Enpal] Wallbox-Sensoren hinzugefügt")



    async_add_entities(entities)


class EnpalSensor(SensorEntity):
    def __init__(self, uid: str, sensor: dict, coordinator: DataUpdateCoordinator):
        self._attr_name = sensor["name"]
        self._attr_unique_id = uid
        try:
            self._attr_native_value = float(sensor["value"])
        except ValueError:
            self._attr_native_value = sensor["value"]
        self._attr_native_unit_of_measurement = sensor["unit"]
        self._attr_device_class = sensor["device_class"]
        if self._attr_device_class == "energy":
            self._attr_state_class = "total_increasing"
        self._attr_should_poll = False
        self._attr_enabled_default = sensor["enabled"]
        self._attr_extra_state_attributes = {
            "enpal_last_update": sensor.get("enpal_last_update")
        }
        self._coordinator = coordinator

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "enpal_device")},
            "name": "Enpal Webgerät",
            "manufacturer": "Enpal",
            "model": "Webparser",
        }

    async def async_update(self):
        await self._coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        self._coordinator.async_add_listener(self._handle_coordinator_update)

    def _handle_coordinator_update(self):
        for sensor in self._coordinator.data:
            if make_id(sensor["name"]) == self._attr_unique_id:
                try:
                    self._attr_native_value = float(sensor["value"])
                except ValueError:
                    self._attr_native_value = sensor["value"]
                self._attr_extra_state_attributes["enpal_last_update"] = sensor.get("enpal_last_update")
                break
        self.async_write_ha_state()




class CumulativeEnergySensor(SensorEntity, RestoreEntity):
    def __init__(self, hass: HomeAssistant, coordinator: DataUpdateCoordinator, sensor_name: str, interval_seconds: int):
        self.hass = hass
        self._attr_name = "Inverter: Energy produced total (DC)"
        self._attr_unique_id = "cumulative_energy_produced_dc_kwh"
        self._attr_device_class = "energy"
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
    def native_value(self):
        return round(self._value or 0.0, 3)


    @property
    def extra_state_attributes(self):
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
                    self._value += energy_kwh
                    self._last_updated = datetime.now().isoformat()
                    _LOGGER.debug("[Enpal] +%.5f kWh -> Total: %.3f", energy_kwh, self._state["value"])
                except Exception as e:
                    _LOGGER.warning("[Enpal] Error in energy calculation: %s", e)
                break
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "enpal_device")},
            "name": "Enpal Webgerät",
            "manufacturer": "Enpal",
            "model": "Webparser",
        }




class DailyResetFromEntitySensor(SensorEntity, RestoreEntity):
    def __init__(self, hass: HomeAssistant, source_entity_id: str):
        self.hass = hass
        self._attr_name = "Inverter: Energy produced today (DC)"
        self._attr_unique_id = "daily_energy_produced_dc_kwh"
        self._attr_device_class = "energy"
        self._attr_state_class = "total"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_icon = "mdi:calendar-refresh"
        self._source_entity_id = source_entity_id
        self._today_start_value = None
        self._value = 0.0
        self._last_reset = datetime.now().date()

    @property
    def native_value(self):
        return round(self._value or 0.0, 3)

    @property
    def extra_state_attributes(self):
        return {
            "last_reset": self._last_reset.isoformat(),
            "start_value": self._today_start_value if self._today_start_value is not None else "Not set"
        }

    async def async_added_to_hass(self):
        await RestoreEntity.async_added_to_hass(self)
        # Statt self.hass.helpers.event.async_track_state_change_event(...),
        # verwende den importierten async_track_state_change_event:
        
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

    def _try_float(self, val):
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

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "enpal_device")},
            "name": "Enpal Webgerät",
            "manufacturer": "Enpal",
            "model": "Webparser",
        }



class WallboxCoordinatorEntity(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, name, unique_id, key):
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._key = key
        self._attr_icon = "mdi:ev-station"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "enpal_device")},
            "name": "Enpal Webgerät",
            "manufacturer": "Enpal",
            "model": "Webparser",
        }

    @property
    def native_value(self):
        if self.coordinator.data:
            return self.coordinator.data.get(self._key)
        return None


class WallboxModeSensor(WallboxCoordinatorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Wallbox Lademodus", "wallbox_mode", "mode")


class WallboxStatusSensor(WallboxCoordinatorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Wallbox Status", "wallbox_status", "status")
