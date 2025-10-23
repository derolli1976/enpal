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
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .wallbox_api import WallboxApiClient


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

    api_client = WallboxApiClient(hass)

    buttons = [
        EnpalWallboxButton(hass, api_client, "Ladevorgang starten", "start", "start"),
        EnpalWallboxButton(hass, api_client, "Ladevorgang stoppen", "stop", "stop"),
    ]

    for key, label in MODES.items():
        button_name = f"Modus {label} aktivieren"
        buttons.append(EnpalWallboxButton(hass, api_client, button_name, f"set_{key}", f"set_{key}"))
        _LOGGER.debug("[Enpal] Added button for mode: %s", button_name)

    async_add_entities(buttons)
    _LOGGER.info("[Enpal] Wallbox buttons successfully added")


class EnpalWallboxButton(ButtonEntity):
    def __init__(self, hass, api_client: WallboxApiClient, name: str, action: str, unique_id: str):
        """Initialize the wallbox button.
        
        Args:
            hass: Home Assistant instance
            api_client: Wallbox API client instance
            name: Display name for the button
            action: Action to perform (start, stop, set_eco, set_solar, set_full)
            unique_id: Unique identifier for the entity
        """
        self._hass = hass
        self._api_client = api_client
        self._action = action
        self._attr_name = f"Wallbox {name}"
        self._attr_unique_id = f"enpal_wallbox_button_{unique_id}"
        self._attr_entity_category = EntityCategory.CONFIG
        _LOGGER.debug("[Enpal] Created button entity: %s (action: %s)", self._attr_name, self._action)

    @cached_property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "enpal_device")},
            name="Enpal Webgerät",
            manufacturer="Enpal",
            model="Webparser",
        )

    async def async_press(self):
        """Handle button press."""
        _LOGGER.info("[Enpal] Button pressed: %s", self._attr_name)
        
        # Map action to API client method
        action_map = {
            "start": self._api_client.start_charging,
            "stop": self._api_client.stop_charging,
            "set_eco": self._api_client.set_mode_eco,
            "set_solar": self._api_client.set_mode_solar,
            "set_full": self._api_client.set_mode_full,
        }
        
        api_method = action_map.get(self._action)
        if not api_method:
            _LOGGER.error("[Enpal] Unknown action: %s", self._action)
            return
        
        # Call API and refresh sensors
        endpoint = f"/{self._action}"
        await self._api_client.call_and_refresh_sensors(
            endpoint,
            sensor_entities=[
                "sensor.wallbox_lademodus",
                "sensor.wallbox_status",
            ]
        )
