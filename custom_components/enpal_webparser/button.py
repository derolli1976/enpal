# pyright: reportIncompatibleVariableOverride=false
#
# Home Assistant Custom Component: Enpal Webparser
#
# File: button.py
#
# Description:
#   Home Assistant button platform for Enpal wallbox actions.
#   Provides start/stop charging and mode selection buttons for Enpal wallbox integration.
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
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, DEFAULT_WALLBOX_API_ENDPOINT


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

    base_url = DEFAULT_WALLBOX_API_ENDPOINT

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
        self._hass = hass
        self._attr_name = f"Wallbox {name}"
        self._url = url
        self._attr_unique_id = f"enpal_wallbox_button_{unique_id}"
        self._attr_entity_category = EntityCategory.CONFIG
        _LOGGER.debug("[Enpal] Created button entity: %s (URL: %s)", self._attr_name, self._url)

    @cached_property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "enpal_device")},
            name="Enpal Webgerät",
            manufacturer="Enpal",
            model="Webparser",
        )

    async def async_press(self):
        _LOGGER.info("[Enpal] Button pressed: %s", self._attr_name)
        try:
            session = async_get_clientsession(self._hass)
            async with session.post(self._url, timeout=30) as response:
                if response.status != 200:
                    text = await response.text()
                    _LOGGER.warning("[Enpal] Wallbox command failed (%s): %s", response.status, text)
                else:
                    _LOGGER.info("[Enpal] Wallbox command successful: %s", self._url)
        except Exception as e:
            _LOGGER.exception("[Enpal] Wallbox request failed: %s", e)

        await self._hass.services.async_call(
            "homeassistant",
            "update_entity",
            {
                "entity_id": [
                    "sensor.wallbox_lademodus",
                    "sensor.wallbox_status",
                ]
            },
            blocking=True
        )
