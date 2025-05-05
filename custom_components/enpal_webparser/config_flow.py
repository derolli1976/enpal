import logging
import voluptuous as vol
import requests
from urllib.parse import urlparse

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, DEFAULT_URL, DEFAULT_INTERVAL, DEFAULT_GROUPS, DEFAULT_USE_WALLBOX_ADDON

_LOGGER = logging.getLogger(__name__)


def is_valid_enpal_url_format(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "http" and bool(parsed.netloc)

def validate_enpal_url(url: str) -> bool:
    try:
        resp = requests.get(url, timeout=5)
        return resp.status_code == 200
    except Exception as e:
        _LOGGER.warning(f"[Enpal] URL nicht erreichbar: {e}")
        return False

def sanitize_and_validate_url(raw_url: str) -> tuple[str, str | None]:
    url = raw_url.strip()
    if not url.endswith("/deviceMessages"):
        url = url.rstrip("/") + "/deviceMessages"
    if not is_valid_enpal_url_format(url):
        return url, "invalid_format"
    # if not validate_enpal_url(url):
    #    return url, "unreachable"
    return url, None


class EnpalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        _LOGGER.info("[Enpal] Config flow gestartet")
        errors = {}

        url_input = DEFAULT_URL
        interval_input = DEFAULT_INTERVAL
        groups_input = DEFAULT_GROUPS
        use_wallbox_addon = DEFAULT_USE_WALLBOX_ADDON

        if user_input is not None:
            url_input = user_input.get("url", DEFAULT_URL)
            interval_input = user_input.get("interval", DEFAULT_INTERVAL)
            groups_input = user_input.get("groups", DEFAULT_GROUPS)
            use_wallbox_addon = user_input.get("use_wallbox_addon", DEFAULT_USE_WALLBOX_ADDON)

            url_checked, error = sanitize_and_validate_url(url_input)
            if error:
                errors["url"] = error
            else:
                return self.async_create_entry(
                    title="Enpal Webparser",
                    data={"use_options_flow": True},
                    options={
                        "url": url_checked,
                        "interval": interval_input,
                        "groups": groups_input,
                        "use_wallbox_addon": use_wallbox_addon,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("url", default=url_input): str,
                vol.Required("interval", default=interval_input): int,
                vol.Optional("groups", default=groups_input): cv.multi_select(DEFAULT_GROUPS),
                vol.Optional("use_wallbox_addon", default=DEFAULT_USE_WALLBOX_ADDON): bool,
            }),
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EnpalOptionsFlowHandler(config_entry)


class EnpalOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        _LOGGER.info("[Enpal] OptionsFlow gestartet")
        errors = {}

        current = self.config_entry.options

        url_input = current.get("url", DEFAULT_URL)
        interval_input = current.get("interval", DEFAULT_INTERVAL)
        groups_input = current.get("groups", DEFAULT_GROUPS)
        use_wallbox_addon = current.get("use_wallbox_addon", False)

        if user_input:
            url_input = user_input.get("url", url_input)
            interval_input = user_input.get("interval", interval_input)
            groups_input = user_input.get("groups", groups_input)
            use_wallbox_addon = user_input.get("use_wallbox_addon", use_wallbox_addon)

            url_checked, error = sanitize_and_validate_url(url_input)
            if error:
                errors["url"] = error
            else:
                return self.async_create_entry(title="", data={
                    "url": url_checked,
                    "interval": interval_input,
                    "groups": groups_input,
                    "use_wallbox_addon": use_wallbox_addon, 
                })

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("url", default=url_input): str,
                vol.Required("interval", default=interval_input): int,
                vol.Optional("groups", default=groups_input): cv.multi_select(DEFAULT_GROUPS),
                vol.Optional("use_wallbox_addon", default=False): bool,
            }),
            errors=errors
        )