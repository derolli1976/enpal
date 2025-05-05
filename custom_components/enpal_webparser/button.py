import logging
import requests
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

    base_url = "http://localhost:8090/wallbox"
    buttons = [
        EnpalWallboxButton("Start Charging", f"{base_url}/start", "start"),
        EnpalWallboxButton("Stop Charging", f"{base_url}/stop", "stop"),
    ]
    for key, label in MODES.items():
        buttons.append(EnpalWallboxButton(f"Set {label}", f"{base_url}/set_{key}", f"set_{key}"))

    async_add_entities(buttons)

class EnpalWallboxButton(ButtonEntity):
    def __init__(self, name, url, unique_id):
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
            response = requests.post(self._url, timeout=5)
            if not response.ok:
                _LOGGER.warning("Wallbox command failed: %s", response.text)
        except Exception as e:
            _LOGGER.error("Wallbox request failed: %s", e)