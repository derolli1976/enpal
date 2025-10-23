# pyright: reportIncompatibleVariableOverride=false
#
# Home Assistant Custom Component: Enpal Webparser
#
# File: switch.py
#
# Description:
#   Home Assistant switch platform for Enpal wallbox control.
#   Allows toggling wallbox charging via Home Assistant and triggers status updates.
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
from functools import cached_property
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN
from .wallbox_api import WallboxApiClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    if not config_entry.options.get("use_wallbox_addon", False):
        return

    api_client = WallboxApiClient(hass)
    async_add_entities([EnpalWallboxSwitch(hass, api_client)], True)


class EnpalWallboxSwitch(SwitchEntity):
    def __init__(self, hass, api_client: WallboxApiClient):
        """Initialize the wallbox switch.
        
        Args:
            hass: Home Assistant instance
            api_client: Wallbox API client instance
        """
        self._hass = hass
        self._api_client = api_client
        self._attr_name = "Wallbox Charging"
        self._attr_unique_id = "enpal_wallbox_charging_switch"
        self._is_on = False
        self._pending_state = None

    @property
    def is_on(self):
        if self._pending_state is not None:
            return self._pending_state
        return self._is_on if self._is_on is not None else False


    @cached_property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "enpal_device")},
            name="Enpal Webgerät",
            manufacturer="Enpal",
            model="Webparser",
        )

    async def async_added_to_hass(self):
        """Automatisch aufgerufen, wenn die Entität registriert wird."""
        async_track_state_change_event(
            self._hass,
            "sensor.wallbox_status",
            self._handle_wallbox_status_change
        )
        await self.async_update()

    async def _handle_wallbox_status_change(self, event):
        """Reagiere auf Änderungen des sensor.wallbox_status."""
        _LOGGER.debug("Detected state change for wallbox_status: %s", event.data)
        await self.async_update()
        self.async_write_ha_state()

    async def async_update(self):
        status_entity = self._hass.states.get("sensor.wallbox_status")
        if not status_entity or status_entity.state in ("unavailable", "unknown", None):
            _LOGGER.warning("sensor.wallbox_status not found or unavailable")
            self._is_on = False  
            return

        status = status_entity.state.lower()
        new_state = status == "charging"

        if self._pending_state is not None:
            if self._pending_state == new_state:
                _LOGGER.debug("Wallbox switch state confirmed by sensor: %s", status)
                self._is_on = new_state
                self._pending_state = None
            else:
                _LOGGER.debug("Wallbox switch state pending: requested=%s, sensor=%s", self._pending_state, new_state)
        else:
            self._is_on = new_state

    async def async_turn_on(self, **kwargs):
        """Turn on the wallbox charging."""
        success = await self._api_client.call_and_refresh_sensors(
            "/start",
            sensor_entities=[
                "sensor.wallbox_status",
                "sensor.wallbox_lademodus"
            ]
        )
        if success:
            self._pending_state = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn off the wallbox charging."""
        success = await self._api_client.call_and_refresh_sensors(
            "/stop",
            sensor_entities=[
                "sensor.wallbox_status",
                "sensor.wallbox_lademodus"
            ]
        )
        if success:
            self._pending_state = False
            self.async_write_ha_state()
