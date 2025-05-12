import logging
import voluptuous as vol
from urllib.parse import urlparse
import aiohttp

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, DEFAULT_URL, DEFAULT_INTERVAL, DEFAULT_GROUPS, DEFAULT_USE_WALLBOX_ADDON, DEFAULT_WALLBOX_API_ENDPOINT

_LOGGER = logging.getLogger(__name__)


def is_valid_enpal_url_format(url: str) -> bool:
    parsed = urlparse(url)
    valid = parsed.scheme == "http" and bool(parsed.netloc)
    _LOGGER.debug("[Enpal] URL format valid: %s -> %s", url, valid)
    return valid


def sanitize_url(raw_url: str) -> tuple[str, str | None]:
    url = raw_url.strip()
    if not url.endswith("/deviceMessages"):
        url = url.rstrip("/") + "/deviceMessages"
        _LOGGER.debug("[Enpal] URL adjusted to: %s", url)
    if not is_valid_enpal_url_format(url):
        _LOGGER.warning("[Enpal] Invalid URL format: %s", url)
        return url, "invalid_format"
    return url, None


async def validate_enpal_url(url: str) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                _LOGGER.info("[Enpal] URL reachable, status: %s", response.status)
                return response.status == 200
    except Exception as e:
        _LOGGER.warning("[Enpal] URL not reachable: %s", e)
        return False


async def validate_wallbox_api() -> bool:
    url = f"{DEFAULT_WALLBOX_API_ENDPOINT}/status"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=45) as response:
                if response.status != 200:
                    _LOGGER.warning("[Enpal] Wallbox API HTTP error: %s", response.status)
                    return False
                data = await response.json()
                success = data.get("success", False)
                _LOGGER.info("[Enpal] Wallbox API success: %s", success)
                return success is True
    except Exception as e:
        _LOGGER.warning("[Enpal] Wallbox API not reachable: %s", e)
        return False


class EnpalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        _LOGGER.info("[Enpal] Config flow started")
        errors = {}

        url_input = DEFAULT_URL
        interval_input = DEFAULT_INTERVAL
        groups_input = DEFAULT_GROUPS
        use_wallbox_addon = DEFAULT_USE_WALLBOX_ADDON

        if user_input is not None:
            _LOGGER.debug("[Enpal] User input: %s", user_input)
            url_input = user_input.get("url", DEFAULT_URL)
            interval_input = user_input.get("interval", DEFAULT_INTERVAL)
            groups_input = user_input.get("groups", DEFAULT_GROUPS)
            use_wallbox_addon = user_input.get("use_wallbox_addon", DEFAULT_USE_WALLBOX_ADDON)

            _LOGGER.debug("[Enpal] Parsed user options - URL: %s, Interval: %s, Groups: %s, Use Wallbox Add-on: %s",
                          url_input, interval_input, groups_input, use_wallbox_addon)

            url_checked, error = sanitize_url(url_input)
            if not error:
                if not await validate_enpal_url(url_checked):
                    error = "unreachable"

            if error:
                errors["url"] = error
                _LOGGER.warning("[Enpal] Invalid URL input: %s (%s)", url_input, error)
            elif use_wallbox_addon and not await validate_wallbox_api():
                errors["use_wallbox_addon"] = "wallbox_unreachable"
            else:
                _LOGGER.info("[Enpal] URL validated: %s", url_checked)
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
        _LOGGER.info("[Enpal] OptionsFlow started")
        errors = {}

        current = self.config_entry.options

        url_input = current.get("url", DEFAULT_URL)
        interval_input = current.get("interval", DEFAULT_INTERVAL)
        groups_input = current.get("groups", DEFAULT_GROUPS)
        use_wallbox_addon = current.get("use_wallbox_addon", DEFAULT_USE_WALLBOX_ADDON)

        if user_input:
            _LOGGER.debug("[Enpal] OptionsFlow input: %s", user_input)
            url_input = user_input.get("url", url_input)
            interval_input = user_input.get("interval", interval_input)
            groups_input = user_input.get("groups", groups_input)
            use_wallbox_addon = user_input.get("use_wallbox_addon", use_wallbox_addon)

            _LOGGER.debug("[Enpal] Parsed options - URL: %s, Interval: %s, Groups: %s, Use Wallbox Add-on: %s",
                          url_input, interval_input, groups_input, use_wallbox_addon)

            url_checked, error = sanitize_url(url_input)
            if not error:
                if not await validate_enpal_url(url_checked):
                    error = "unreachable"

            if error:
                errors["url"] = error
                _LOGGER.warning("[Enpal] Invalid URL in OptionsFlow: %s (%s)", url_input, error)
            elif use_wallbox_addon and not await validate_wallbox_api():
                errors["use_wallbox_addon"] = "wallbox_unreachable"
            else:
                _LOGGER.info("[Enpal] URL in OptionsFlow validated: %s", url_checked)
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
                vol.Optional("use_wallbox_addon", default=use_wallbox_addon): bool,
            }),
            errors=errors
        )
