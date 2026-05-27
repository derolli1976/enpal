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
import time
from functools import cached_property

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN, WALLBOX_LEGACY_MODE_MAP, WALLBOX_MODE_MAP
from .wallbox_api import WallboxApiClient

_LOGGER = logging.getLogger(__name__)

# UI → API
REVERSE_MODE_MAP = {v.lower(): k for k, v in WALLBOX_MODE_MAP.items()}


async def async_setup_entry(hass, config_entry, async_add_entities):
    if not config_entry.options.get("use_wallbox", False):
        return

    # Use shared wallbox client from entry data
    entry_data = hass.data[DOMAIN].get(config_entry.entry_id, {})
    api_client = entry_data.get("wallbox_client")
    if api_client is None:
        _LOGGER.error("[Enpal] No wallbox client available, skipping select setup")
        return

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
        self._pending_since: float = 0  # monotonic timestamp when pending was set
        # Minimum seconds a pending change is protected from being overwritten
        # by a stale coordinator poll that still reports the old state.
        self._pending_grace_period: float = 10.0

    async def async_added_to_hass(self):
        """Register state change listener when entity is added."""
        async_track_state_change_event(
            self._hass,
            "sensor.wallbox_lademodus",
            self._handle_mode_change
        )
        await self.async_update()

    async def _handle_mode_change(self, event):
        """React to sensor.wallbox_lademodus state changes."""
        _LOGGER.debug("[Enpal] Detected state change for wallbox_lademodus: %s", event.data)
        await self.async_update()
        self.async_write_ha_state()

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
            # Don't clear _current_option if we have a pending change — keeps UI stable
            if not self._pending_change:
                self._current_option = None
            return

        mode = mode_entity.state.lower()
        mode = WALLBOX_LEGACY_MODE_MAP.get(mode, mode)
        new_option = WALLBOX_MODE_MAP.get(mode)

        if not new_option:
            _LOGGER.warning("Unknown wallbox mode from sensor: %s", mode)
            return

        if self._pending_change:
            if self._pending_change == new_option:
                _LOGGER.debug("Pending wallbox mode %s confirmed by sensor.", new_option)
                self._current_option = new_option
                self._pending_change = None
                self._pending_since = 0
            else:
                elapsed = time.monotonic() - self._pending_since
                if elapsed < self._pending_grace_period:
                    # Still within grace period — ignore stale sensor value
                    _LOGGER.debug(
                        "Wallbox mode change pending (%.1fs/%ss): %s (sensor reports %s)",
                        elapsed, self._pending_grace_period,
                        self._pending_change, new_option,
                    )
                else:
                    # Grace period expired — accept the sensor value
                    _LOGGER.info(
                        "Wallbox pending mode %s not confirmed after %.0fs, accepting sensor value %s",
                        self._pending_change, elapsed, new_option,
                    )
                    self._current_option = new_option
                    self._pending_change = None
                    self._pending_since = 0
        else:
            self._current_option = new_option

    async def async_select_option(self, option: str):
        """Handle mode selection."""
        key = REVERSE_MODE_MAP.get(option.lower())
        if not key:
            _LOGGER.warning("[Enpal] Unknown selected option: %s", option)
            return
        
        self._pending_change = option
        self._pending_since = time.monotonic()
        self.async_write_ha_state()

        # Call API and refresh coordinator directly
        success = await self._api_client.call_and_refresh_sensors(
            f"/set_{key}",
        )
        if not success:
            _LOGGER.warning("[Enpal] Mode change to %s failed, clearing pending state", option)
            self._pending_change = None
            self._pending_since = 0
            self.async_write_ha_state()
