import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    if not config_entry.options.get("use_wallbox_addon", False):
        return

    async_add_entities([EnpalWallboxSwitch(hass)], True)

class EnpalWallboxSwitch(SwitchEntity):
    def __init__(self, hass):
        self._hass = hass
        self._attr_name = "Wallbox Charging"
        self._attr_unique_id = "enpal_wallbox_charging_switch"
        self._is_on = False
        self._pending_state = None
        self._base_url = "http://localhost:36725/wallbox"

    @property
    def is_on(self):
        return self._pending_state if self._pending_state is not None else self._is_on
    
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "enpal_device")},
            "name": "Enpal Webgerät",
            "manufacturer": "Enpal",
            "model": "Webparser",
        }

    async def async_update(self):
        status_entity = self._hass.states.get("sensor.wallbox_status")
        if not status_entity:
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
        await self._call_wallbox_api("/start")
        self._pending_state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._call_wallbox_api("/stop")
        self._pending_state = False
        self.async_write_ha_state()

    async def _call_wallbox_api(self, endpoint):
        url = f"{self._base_url}{endpoint}"
        try:
            session = async_get_clientsession(self._hass)
            async with session.post(url, timeout=5) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Wallbox API call failed: %s", url)
        except Exception as e:
            _LOGGER.error("Error calling wallbox API endpoint %s: %s", endpoint, e)
