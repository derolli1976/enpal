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

import asyncio
import logging
from functools import cached_property

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, WALLBOX_MODE_MAP
from .wallbox_api import WallboxApiClient

_LOGGER = logging.getLogger(__name__)

# UI → API
REVERSE_MODE_MAP = {v.lower(): k for k, v in WALLBOX_MODE_MAP.items()}


async def async_setup_entry(hass, config_entry, async_add_entities):
    if not config_entry.options.get("use_wallbox_addon", False):
        return

    api_client = WallboxApiClient(hass)
    async_add_entities([EnpalWallboxModeSelect(hass, api_client)], True)


class EnpalWallboxModeSelect(SelectEntity):
    def __init__(self, hass, api_client: WallboxApiClient):
        """Initialize the wallbox mode selector.
        
        Args:
            hass: Home Assistant instance
            api_client: Wallbox API client instance
        """
        self._hass = hass
        self._api_client = api_client
        self._attr_name = "Wallbox Mode"
        self._attr_unique_id = "enpal_wallbox_mode_select"
        self._attr_options = list(WALLBOX_MODE_MAP.values())
        self._current_option = None
        self._pending_change = None

    
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
        """Handle mode selection."""
        key = REVERSE_MODE_MAP.get(option.lower())
        if not key:
            _LOGGER.warning("[Enpal] Unknown selected option: %s", option)
            return
        
        self._pending_change = option
        self.async_write_ha_state()

        # Call API and refresh sensors
        await self._api_client.call_and_refresh_sensors(
            f"/set_{key}",
            sensor_entities=["sensor.wallbox_lademodus"]
        )
