from homeassistant import config_entries
import voluptuous as vol

from .const import DOMAIN, DEFAULT_URL, DEFAULT_INTERVAL, DEFAULT_GROUPS

class EnpalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title="Enpal Webparser",
                data={
                    "url": user_input["url"],
                    "interval": user_input["interval"],
                    "groups": user_input["groups"],
                },
            )

        schema = vol.Schema({
            vol.Required("url", default=DEFAULT_URL): str,
            vol.Required("interval", default=DEFAULT_INTERVAL): int,
            vol.Required("groups", default=DEFAULT_GROUPS): vol.All(
                vol.EnsureList,
                vol.In(["Wallbox", "Battery", "Inverter", "Site Data", "IoTEdgeDevice", "PowerSensor"]),
            )
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
