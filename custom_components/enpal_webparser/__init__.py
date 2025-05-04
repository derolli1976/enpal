from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigEntries
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    _LOGGER.info("[Enpal] async_setup aufgerufen")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("[Enpal] async_setup_entry gestartet")
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    await hass.config_entries.async_forward_entry_setup(entry, "sensor")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("[Enpal] async_unload_entry aufgerufen")
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return await hass.config_entries.async_forward_entry_unload(entry, "sensor")
