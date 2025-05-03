from datetime import timedelta
import re
import logging
import aiohttp
from bs4 import BeautifulSoup

from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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

    url = entry.data.get("url", DEFAULT_URL)
    interval = entry.data.get("interval", DEFAULT_INTERVAL)
    groups = entry.data.get("groups", [])

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
                            "enabled": group in groups
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

    await coordinator.async_config_entry_first_refresh()

    entities = []
    for sensor in coordinator.data:
        uid = make_id(sensor["name"])
        _LOGGER.debug(f"[Enpal] Sensor hinzugefügt: {sensor['name']}")
        entities.append(EnpalSensor(uid, sensor, coordinator))

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
        self._attr_should_poll = False
        self._attr_enabled_default = sensor["enabled"]
        self._coordinator = coordinator

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "enpal_device")},
            "name": "Enpal Webgerät",
            "manufacturer": "Enpal",
            "model": "Webparser",
            "entry_type": "service",
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
                break
        self.async_write_ha_state()
