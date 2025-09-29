# pyright: reportIncompatibleVariableOverride=false
#
# Home Assistant Custom Component: Enpal Webparser
#
# File: config_flow.py
#
# Description:
#   Home Assistant config flow for Enpal Webparser integration.
#   Provides setup and options dialogs for configuring URL, interval, groups, and wallbox add-on usage.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
# Repository:   https://github.com/derolli1976/enpal
#
# Compatible with Home Assistant Core 2024.x and later.
#
# See README.md for setup and usage instructions.
#

import logging
from typing import Any, cast
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DEFAULT_GROUPS,
    DEFAULT_INTERVAL,
    DEFAULT_URL,
    DEFAULT_USE_WALLBOX_ADDON,
    DEFAULT_WALLBOX_API_ENDPOINT,
    DOMAIN,
)

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


async def validate_enpal_url(hass, url: str) -> bool:
    try:
        session = async_get_clientsession(hass)
        async with session.get(url, timeout=30) as response:
            _LOGGER.info("[Enpal] URL reachable, status: %s", response.status)
            return response.status == 200
    except Exception as e:
        _LOGGER.warning("[Enpal] URL not reachable: %s", e)
        return False


async def validate_wallbox_api(hass) -> bool:
    url = f"{DEFAULT_WALLBOX_API_ENDPOINT}/status"
    try:
        session = async_get_clientsession(hass)
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


def get_default_config(options: dict[str, Any] | None = None) -> dict[str, Any]:
    src = dict(options) if options is not None else {}
    return {
        "url": src.get("url", DEFAULT_URL),
        "interval": src.get("interval", DEFAULT_INTERVAL),
        "groups": src.get("groups", DEFAULT_GROUPS),
        "use_wallbox_addon": src.get("use_wallbox_addon", DEFAULT_USE_WALLBOX_ADDON),
    }


def get_form_schema(config: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("url", default=cast(Any, config["url"])): str,
            vol.Required("interval", default=cast(Any, config["interval"])): int,
            vol.Optional("groups", default=cast(Any, config["groups"])): cv.multi_select(DEFAULT_GROUPS),
            vol.Optional("use_wallbox_addon", default=cast(Any, config["use_wallbox_addon"])): bool,
        }
    )


async def process_user_input(hass, user_input: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, str]]:
    errors: dict[str, str] = {}
    url_input = user_input["url"]
    url_checked, error = sanitize_url(url_input)

    if not error and not await validate_enpal_url(hass, url_checked):
        error = "unreachable"

    if error:
        errors["url"] = error
    elif user_input.get("use_wallbox_addon") and not await validate_wallbox_api(hass):
        errors["use_wallbox_addon"] = "wallbox_unreachable"

    if errors:
        return None, errors

    return {
        "url": url_checked,
        "interval": user_input["interval"],
        "groups": user_input.get("groups", DEFAULT_GROUPS),
        "use_wallbox_addon": user_input.get("use_wallbox_addon", False),
    }, {}


class EnpalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        _LOGGER.info("[Enpal] Config flow started")
        config = get_default_config()
        errors: dict[str, str] = {}

        if user_input is not None:
            _LOGGER.debug("[Enpal] User input: %s", user_input)
            result, errors = await process_user_input(self.hass, user_input)
            if result:
                return self.async_create_entry(
                    title="Enpal Webparser",
                    data={"use_options_flow": True},
                    options=result,
                )
            config.update(user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=get_form_schema(config),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EnpalOptionsFlowHandler(config_entry)


class EnpalOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        _LOGGER.info("[Enpal] OptionsFlow started")
        config = get_default_config(dict(self._config_entry.options))
        errors: dict[str, str] = {}

        if user_input:
            _LOGGER.debug("[Enpal] OptionsFlow input: %s", user_input)
            result, errors = await process_user_input(self.hass, user_input)
            if result:
                return self.async_create_entry(title="", data=result)
            config.update(user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=get_form_schema(config),
            errors=errors,
        )
