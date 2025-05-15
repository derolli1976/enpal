import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    _LOGGER.info("[Enpal] async_setup called during Home Assistant startup")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("[Enpal] async_setup_entry started for entry_id: %s", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})

    use_wallbox_addon = entry.options.get("use_wallbox_addon", False)
    
    platforms = ["sensor"]
    if use_wallbox_addon:
        platforms.extend(["button", "switch", "select"])

    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "platforms": platforms,
    }

    _LOGGER.debug("[Enpal] Entry options: %s", entry.options)
    _LOGGER.info("[Enpal] Setting up platforms for entry: %s", platforms)

    try:
        await hass.config_entries.async_forward_entry_setups(entry, platforms)
    except Exception as e:
        _LOGGER.exception("[Enpal] Failed to set up entry platforms: %s", e)
        raise ConfigEntryNotReady(f"Error setting up entry: {e}")

    _LOGGER.info("[Enpal] async_setup_entry completed successfully for entry_id: %s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("[Enpal] async_unload_entry called for entry_id: %s", entry.entry_id)

    platforms = hass.data[DOMAIN].get(entry.entry_id, {}).get("platforms", [])
    _LOGGER.debug("[Enpal] Unloading platforms: %s", platforms)

    unloaded = await hass.config_entries.async_unload_platforms(entry, platforms)

    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.info("[Enpal] Entry %s unloaded and data cleaned up", entry.entry_id)
    else:
        _LOGGER.warning("[Enpal] Failed to unload entry %s", entry.entry_id)

    return unloaded
