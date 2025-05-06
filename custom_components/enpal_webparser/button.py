import logging
import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

MODES = {
    "eco": "Eco",
    "full": "Full",
    "solar": "Solar",
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    if not config_entry.options.get("use_wallbox_addon", False):
        return
    options = config_entry.options
    if not options.get("use_wallbox_addon", False):
        return

    base_url = "http://localhost:36725/wallbox"
    buttons = [
        EnpalWallboxButton(hass, "Start Charging", f"{base_url}/start", "start"),
        EnpalWallboxButton(hass, "Stop Charging", f"{base_url}/stop", "stop"),
    ]
    for key, label in MODES.items():
        buttons.append(EnpalWallboxButton(hass, f"Set {label}", f"{base_url}/set_{key}", f"set_{key}"))

    async_add_entities(buttons)

class EnpalWallboxButton(ButtonEntity):
    def __init__(self, hass, name, url, unique_id):
        self.hass = hass
        self._attr_name = f"Wallbox {name}"
        self._url = url
        self._attr_unique_id = f"enpal_wallbox_button_{unique_id}"
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "enpal_device")},
            "name": "Enpal Webgerät",
            "manufacturer": "Enpal",
            "model": "Webparser",
        }

    async def async_press(self):
        try:
            session = async_get_clientsession(self.hass)
            async with session.post(self._url, timeout=5) as response:
                if response.status != 200:
                    _LOGGER.warning("Wallbox command failed: %s", await response.text())
        except Exception as e:
            _LOGGER.error("Wallbox request failed: %s", e)
        # Sensor-Update anstoßen
        coordinator = self.hass.data[DOMAIN].get("coordinator")
        if coordinator:
            await coordinator.async_request_refresh()