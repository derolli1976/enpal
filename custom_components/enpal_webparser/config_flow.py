import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, DEFAULT_URL, DEFAULT_INTERVAL, DEFAULT_GROUPS

_LOGGER = logging.getLogger(__name__)

GROUP_OPTIONS = ["Wallbox", "Battery", "Inverter", "Site Data", "IoTEdgeDevice", "PowerSensor"]

class EnpalParserFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        _LOGGER.info("Enpal Parser: config flow gestartet")

        if user_input is not None:
            return self.async_create_entry(
                title="Enpal Parser",
                data={
                    "url": user_input.get("url", DEFAULT_URL),
                    "interval": user_input.get("interval", DEFAULT_INTERVAL),
                    "groups": user_input.get("groups", []),
                },
            )

        schema = vol.Schema({
            vol.Required("url", default=DEFAULT_URL): str,
            vol.Required("interval", default=DEFAULT_INTERVAL): int,
            vol.Optional("groups", default=DEFAULT_GROUPS): cv.multi_select(GROUP_OPTIONS)
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors={})
