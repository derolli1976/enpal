# pyright: reportIncompatibleVariableOverride=false
#
# Home Assistant Custom Component: Enpal Webparser
#
# File: __init__.py
#
# Description:
#   Home Assistant integration setup for Enpal Webparser.
#   Handles initial integration setup, config entry setup, and platform loading/unloading.
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

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .wallbox_api import WallboxApiClient

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


def _get_enpal_base_url(options: dict) -> str:
    """Derive the Enpal Box base URL from the configured deviceMessages URL."""
    url = options.get("url", "")
    return url.replace("/deviceMessages", "").rstrip("/")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    _LOGGER.info("[Enpal] async_setup called during Home Assistant startup")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("[Enpal] async_setup_entry started for entry_id: %s", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})

    # Migration: Update existing config options
    new_options = dict(entry.options)
    needs_update = False
    if "data_source" not in new_options:
        _LOGGER.info("[Enpal] Migrating existing config - setting data_source to 'html'")
        new_options["data_source"] = "html"
        needs_update = True
    # Rename use_wallbox_addon -> use_wallbox
    if "use_wallbox_addon" in new_options:
        new_options["use_wallbox"] = new_options.pop("use_wallbox_addon")
        needs_update = True
    if needs_update:
        hass.config_entries.async_update_entry(entry, options=new_options)

    use_wallbox = entry.options.get("use_wallbox", False)
    
    platforms = ["sensor"]
    if use_wallbox:
        platforms.extend(["button", "switch", "select"])

    entry_data = {
        "config": entry.data,
        "platforms": platforms,
    }

    # Create shared wallbox client for all wallbox platforms
    if use_wallbox:
        data_source = entry.options.get("data_source", "html")
        enpal_base_url = _get_enpal_base_url(entry.options)

        if data_source == "websocket":
            # Native Blazor mode: connect directly to Enpal Box /wallbox page
            wallbox_client = WallboxApiClient(
                hass,
                enpal_base_url=enpal_base_url,
                use_native=True,
            )
            _LOGGER.info("[Enpal] Created native wallbox client for %s", enpal_base_url)
        else:
            # Legacy addon mode: HTTP calls to localhost:36725
            wallbox_client = WallboxApiClient(hass, use_native=False)
            _LOGGER.info("[Enpal] Created legacy addon wallbox client")

        entry_data["wallbox_client"] = wallbox_client

    hass.data[DOMAIN][entry.entry_id] = entry_data

    _LOGGER.debug("[Enpal] Entry options: %s", entry.options)
    _LOGGER.info("[Enpal] Setting up platforms for entry: %s", platforms)

    try:
        await hass.config_entries.async_forward_entry_setups(entry, platforms)
    except Exception as e:
        _LOGGER.exception("[Enpal] Failed to set up entry platforms: %s", e)
        raise ConfigEntryNotReady(f"Error setting up entry: {e}")

    # Reload integration when options change (e.g. wallbox enabled/disabled)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.info("[Enpal] async_setup_entry completed successfully for entry_id: %s", entry.entry_id)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options change."""
    _LOGGER.info("[Enpal] Options changed, reloading integration")
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("[Enpal] async_unload_entry called for entry_id: %s", entry.entry_id)

    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})

    # Close wallbox client if exists
    wallbox_client = entry_data.get("wallbox_client")
    if wallbox_client:
        try:
            await wallbox_client.close()
            _LOGGER.info("[Enpal] Wallbox client connection closed")
        except Exception as e:
            _LOGGER.warning("[Enpal] Error closing wallbox client: %s", e)

    # Close API client if exists
    coordinator = hass.data.get(DOMAIN, {}).get("coordinator")
    if coordinator and hasattr(coordinator, 'api_client'):
        try:
            await coordinator.api_client.close()
            _LOGGER.info("[Enpal] API client connection closed")
        except Exception as e:
            _LOGGER.warning("[Enpal] Error closing API client: %s", e)

    platforms = entry_data.get("platforms", [])
    _LOGGER.debug("[Enpal] Unloading platforms: %s", platforms)

    unloaded = await hass.config_entries.async_unload_platforms(entry, platforms)

    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.info("[Enpal] Entry %s unloaded and data cleaned up", entry.entry_id)
    else:
        _LOGGER.warning("[Enpal] Failed to unload entry %s", entry.entry_id)

    return unloaded
