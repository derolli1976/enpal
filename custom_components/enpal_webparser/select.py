import logging

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Mapping: API → UI
MODE_MAP = {
    "eco": "Eco",
    "fast": "Full",
    "solar": "Solar",
}

# UI → API
REVERSE_MODE_MAP = {v.lower(): k for k, v in MODE_MAP.items()}

async def async_setup_entry(hass, config_entry, async_add_entities):
    if not config_entry.options.get("use_wallbox_addon", False):
        return

    async_add_entities([EnpalWallboxModeSelect(hass)], True)

class EnpalWallboxModeSelect(SelectEntity):
    def __init__(self, hass):
        self._hass = hass
        self._attr_name = "Wallbox Mode"
        self._attr_unique_id = "enpal_wallbox_mode_select"
        self._attr_options = list(MODE_MAP.values())
        self._current_option = None
        self._pending_change = None
        self._base_url = "http://localhost:36725/wallbox"

    @property
    def current_option(self):
        return self._pending_change or self._current_option

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "enpal_device")},
            "name": "Enpal Webgerät",
            "manufacturer": "Enpal",
            "model": "Webparser",
        }

    async def async_update(self):
        mode_entity = self._hass.states.get("sensor.wallbox_lademodus")
        if not mode_entity:
            return

        mode = mode_entity.state.lower()
        new_option = MODE_MAP.get(mode)

        if not new_option:
            _LOGGER.warning("Unknown wallbox mode from sensor: %s", mode)
            return

        
        if self._pending_change:
            if self._pending_change == new_option:
        
                _LOGGER.debug("Pending wallbox mode %s confirmed by sensor.", new_option)
                self._current_option = new_option
                self._pending_change = None
            else:
                _LOGGER.debug("Wallbox mode change pending: %s (sensor reports %s)", self._pending_change, new_option)
        else:
            self._current_option = new_option

    async def async_select_option(self, option: str):
        key = REVERSE_MODE_MAP.get(option.lower())
        if key:
            self._pending_change = option
            self.async_write_ha_state()

            await self._call_wallbox_api(f"/set_{key}")

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
