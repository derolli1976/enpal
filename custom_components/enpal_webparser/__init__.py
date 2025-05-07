import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    _LOGGER.info("[Enpal] async_setup aufgerufen")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("[Enpal] async_setup_entry gestartet")
    hass.data.setdefault(DOMAIN, {})
    # Daten und Plattform-Liste sichern
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "platforms": ["sensor"] + (["button"] if entry.options.get("use_wallbox_addon", False) else [])
    }
    platforms = hass.data[DOMAIN][entry.entry_id]["platforms"]

    try:
        await hass.config_entries.async_forward_entry_setups(entry, platforms)
    except Exception as e:
        raise ConfigEntryNotReady(f"Error setting up entry: {e}")

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("[Enpal] async_unload_entry aufgerufen")
    # Nur die tatsächlich gesetzten Plattformen abräumen
    platforms = hass.data[DOMAIN].get(entry.entry_id, {}).get("platforms", [])
    unloaded = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
