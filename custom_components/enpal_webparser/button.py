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
        _LOGGER.debug("[Enpal] Wallbox add-on is disabled, skipping button setup.")
        return

    _LOGGER.info("[Enpal] Setting up Wallbox buttons")
    options = config_entry.options
    base_url = "http://localhost:36725/wallbox"

    buttons = [
        EnpalWallboxButton(hass, "Ladevorgang starten", f"{base_url}/start", "start"),
        EnpalWallboxButton(hass, "Ladevorgang stoppen", f"{base_url}/stop", "stop"),
    ]
    for key, label in MODES.items():
        button_name = f"Modus {label} aktivieren"
        buttons.append(EnpalWallboxButton(hass, button_name, f"{base_url}/set_{key}", f"set_{key}"))
        _LOGGER.debug("[Enpal] Added button for mode: %s", button_name)

    async_add_entities(buttons)
    _LOGGER.info("[Enpal] Wallbox buttons successfully added")


class EnpalWallboxButton(ButtonEntity):
    def __init__(self, hass, name, url, unique_id):
        self.hass = hass
        self._attr_name = f"Wallbox {name}"
        self._url = url
        self._attr_unique_id = f"enpal_wallbox_button_{unique_id}"
        self._attr_entity_category = EntityCategory.CONFIG
        _LOGGER.debug("[Enpal] Created button entity: %s (URL: %s)", self._attr_name, self._url)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "enpal_device")},
            "name": "Enpal Webgerät",
            "manufacturer": "Enpal",
            "model": "Webparser",
        }

    async def async_press(self):
        _LOGGER.info("[Enpal] Button pressed: %s", self._attr_name)
        try:
            session = async_get_clientsession(self.hass)
            async with session.post(self._url, timeout=5) as response:
                if response.status != 200:
                    text = await response.text()
                    _LOGGER.warning("[Enpal] Wallbox command failed (%s): %s", response.status, text)
                else:
                    _LOGGER.info("[Enpal] Wallbox command successful: %s", self._url)
        except Exception as e:
            _LOGGER.exception("[Enpal] Wallbox request failed: %s", e)

        coordinator = self.hass.data[DOMAIN].get("coordinator")
        if coordinator:
            _LOGGER.debug("[Enpal] Triggering coordinator refresh after button press")
            await coordinator.async_request_refresh()
        else:
            _LOGGER.warning("[Enpal] No coordinator found to refresh after button press")
