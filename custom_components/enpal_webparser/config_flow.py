import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, DEFAULT_URL, DEFAULT_INTERVAL, DEFAULT_GROUPS

_LOGGER = logging.getLogger(__name__)


class EnpalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Enpal Webparser."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        _LOGGER.info("[Enpal] Config flow gestartet")

        if user_input is not None:
            # WICHTIG: data darf NICHT leer sein → sonst kein OptionsFlow sichtbar
            return self.async_create_entry(
                title="Enpal Webparser",
                data={"use_options_flow": True},  # ← Dummy-Wert
                options={
                    "url": user_input.get("url", DEFAULT_URL),
                    "interval": user_input.get("interval", DEFAULT_INTERVAL),
                    "groups": user_input.get("groups", DEFAULT_GROUPS),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("url", default=DEFAULT_URL): str,
                vol.Required("interval", default=DEFAULT_INTERVAL): int,
                vol.Optional("groups", default=DEFAULT_GROUPS): cv.multi_select(DEFAULT_GROUPS),
            }),
        )
    
    # Options flow
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EnpalOptionsFlowHandler(config_entry)


class EnpalOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Enpal Webparser."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        _LOGGER.info("[Enpal] OptionsFlow gestartet")

        if user_input:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("url", default=current.get("url", DEFAULT_URL)): str,
                vol.Required("interval", default=current.get("interval", DEFAULT_INTERVAL)): int,
                vol.Optional("groups", default=current.get("groups", DEFAULT_GROUPS)): cv.multi_select(DEFAULT_GROUPS),
            }),
        )



