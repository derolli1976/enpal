# pyright: reportIncompatibleVariableOverride=false
#
# Home Assistant Custom Component: Enpal Webparser
#
# File: select.py
#
# Description:
#   Home Assistant select platform for Enpal wallbox mode selection.
#   Allows users to change charging modes (e.g. eco, solar, full) directly from Home Assistant.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
# Repository:   https://github.com/derolli1976/enpal
#
# Compatible with Home Assistant Core 2024.x and later.
#
# See README.md for setup and usage instructions.
#

import logging
from functools import cached_property

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, DEFAULT_WALLBOX_API_ENDPOINT, WALLBOX_MODE_MAP

_LOGGER = logging.getLogger(__name__)

# UI → API
REVERSE_MODE_MAP = {v.lower(): k for k, v in WALLBOX_MODE_MAP.items()}


async def async_setup_entry(hass, config_entry, async_add_entities):
    if not config_entry.options.get("use_wallbox_addon", False):
        return

    async_add_entities([EnpalWallboxModeSelect(hass)], True)


class EnpalWallboxModeSelect(SelectEntity):
    def __init__(self, hass):
        self._hass = hass
        self._attr_name = "Wallbox Mode"
        self._attr_unique_id = "enpal_wallbox_mode_select"
        self._attr_options = list(WALLBOX_MODE_MAP.values())
        self._current_option = None
        self._pending_change = None
        self._base_url = DEFAULT_WALLBOX_API_ENDPOINT

    
    @property
    def current_option(self) -> str | None:
       return self._pending_change or self._current_option or "Nicht verfügbar"

    @cached_property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "enpal_device")},
            name="Enpal Webgerät",
            manufacturer="Enpal",
            model="Webparser",
        )

    async def async_update(self):
        mode_entity = self._hass.states.get("sensor.wallbox_lademodus")
        if not mode_entity or mode_entity.state in ("unavailable", "unknown", None):
            _LOGGER.warning("sensor.wallbox_lademodus not found or unavailable")
            self._current_option = None
            return

        mode = mode_entity.state.lower()
        new_option = WALLBOX_MODE_MAP.get(mode)

        if not new_option:
            _LOGGER.warning("Unknown wallbox mode from sensor: %s", mode)
            return

        if self._pending_change:
            if self._pending_change == new_option:
                _LOGGER.debug("Pending wallbox mode %s confirmed by sensor.", new_option)
                self._current_option = new_option
                self._pending_change = None
            else:
                _LOGGER.debug(
                    "Wallbox mode change pending: %s (sensor reports %s)",
                    self._pending_change,
                    new_option,
                )
        else:
            self._current_option = new_option

    async def async_select_option(self, option: str):
        key = REVERSE_MODE_MAP.get(option.lower())
        if key:
            self._pending_change = option
            self.async_write_ha_state()

            await self._call_wallbox_api(f"/set_{key}")

            await self._hass.services.async_call(
                "homeassistant",
                "update_entity",
                {"entity_id": "sensor.wallbox_lademodus"},
                blocking=True,
            )
        else:
            _LOGGER.warning("Unknown selected option: %s", option)

    async def _call_wallbox_api(self, endpoint):
        url = f"{self._base_url}{endpoint}"
        try:
            session = async_get_clientsession(self._hass)
            async with session.post(url, timeout=5) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Wallbox API call failed: %s", url)
        except Exception as e:
            _LOGGER.error("Error calling wallbox API endpoint %s: %s", endpoint, e)
