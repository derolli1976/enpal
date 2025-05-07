from datetime import timedelta, datetime
import re
import logging
import aiohttp
from bs4 import BeautifulSoup

from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity, UpdateFailed
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_URL

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
    _LOGGER.info("[Enpal] sensor.py async_setup_entry gestartet")

    url = entry.options.get("url", DEFAULT_URL)
    interval = entry.options.get("interval", DEFAULT_INTERVAL)
    groups = entry.options.get("groups", [])

    async def async_update_data():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    html = await resp.text()

            soup = BeautifulSoup(html, 'html.parser')
            cards = soup.find_all("div", class_="card")

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
                                pass

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

                        sensors.append({
                            "name": friendly_name(group, raw_name),
                            "value": value_clean,
                            "unit": unit,
                            "device_class": device_class,
                            "enabled": group in groups,
                            "enpal_last_update": timestamp_iso
                        })
            _LOGGER.info(f"[Enpal] {len(sensors)} Sensor(en) geladen")
            return sensors
        except Exception as e:
            _LOGGER.error(f"[Enpal] Fehler beim Abruf: {e}")
            raise UpdateFailed(f"Fehler beim Abrufen: {e}")

    coordinator = DataUpdateCoordinator(
        hass,
        logger=_LOGGER,
        name="Enpal Webparser",
        update_method=async_update_data,
        update_interval=timedelta(seconds=interval),
    )

    hass.data[DOMAIN]["coordinator"] = coordinator

    await coordinator.async_config_entry_first_refresh()

    entities = []
    for sensor in coordinator.data:
        uid = make_id(sensor["name"])
        _LOGGER.debug(f"[Enpal] Sensor hinzugefügt: {sensor['name']}")
        entities.append(EnpalSensor(uid, sensor, coordinator))

    
    wallbox_url = "http://127.0.0.1:36725/wallbox/status"
    
    async def async_wallbox_update():
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(wallbox_url, timeout=15) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"Wallbox API Error: {resp.status}")
                    return await resp.json()
        except Exception as e:
            _LOGGER.error(f"[Enpal] Fehler beim Wallbox-Statusabruf: {e}")
            raise UpdateFailed(f"Wallbox-Update fehlgeschlagen: {e}")

    wallbox_coordinator = DataUpdateCoordinator(
        hass,
        logger=_LOGGER,
        name="Wallbox Status",
        update_method=async_wallbox_update,
        update_interval=timedelta(seconds=interval),
    )
    await wallbox_coordinator.async_config_entry_first_refresh()
    
    if entry.options.get("use_wallbox_addon", False):
        entities.extend([
        WallboxModeSensor(wallbox_coordinator),
        WallboxStatusSensor(wallbox_coordinator),
        ])

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
        # Ergänzung für Energiewerte
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
        return self.coordinator.data.get(self._key)

class WallboxModeSensor(WallboxCoordinatorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Wallbox Lademodus", "wallbox_mode", "mode")

class WallboxStatusSensor(WallboxCoordinatorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Wallbox Status", "wallbox_status", "status")
