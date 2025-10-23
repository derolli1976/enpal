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

from .discovery import discover_enpal_devices, quick_discover_enpal_devices
from .wallbox_api import WallboxApiClient
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
    """Validate that the wallbox API is reachable and functional.
    
    Args:
        hass: Home Assistant instance
        
    Returns:
        True if API is available and returns success, False otherwise
    """
    try:
        api_client = WallboxApiClient(hass)
        # Use 15 second timeout to allow addon time to start up
        status_data = await api_client.get_status(timeout=15)
        
        if status_data is None:
            _LOGGER.warning("[Enpal] Wallbox API not reachable")
            return False
        
        success = status_data.get("success", False)
        _LOGGER.info("[Enpal] Wallbox API validation result: %s", success)
        return success is True
        
    except Exception as e:
        _LOGGER.warning("[Enpal] Wallbox API validation failed: %s", e)
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


def get_localized_options(hass, key: str) -> dict[str, str]:
    """Get localized selector options based on user's language.
    
    Args:
        hass: Home Assistant instance
        key: The option key ('setup_mode' or 'discovered_device_none')
    
    Returns:
        Dictionary with option values and localized labels
    """
    language = hass.config.language or "en"
    
    translations = {
        "setup_mode": {
            "en": {
                "discover": "Auto-discover Enpal boxes on network",
                "manual": "Manual setup (enter URL)",
            },
            "de": {
                "discover": "Automatische Erkennung von Enpal-Geräten im Netzwerk",
                "manual": "Manuelle Einrichtung (URL eingeben)",
            },
        },
        "discovered_device_none": {
            "en": {
                "none": "None of these - Enter URL manually",
            },
            "de": {
                "none": "Keines davon - URL manuell eingeben",
            },
        },
        "no_devices": {
            "en": {
                "manual": "No devices found - Enter URL manually",
            },
            "de": {
                "manual": "Keine Geräte gefunden - URL manuell eingeben",
            },
        },
    }
    
    # Default to English if language not found
    return translations.get(key, {}).get(language, translations[key]["en"])


class EnpalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        super().__init__()
        self._discovered_devices = []
        self._discovery_running = False

    async def async_step_user(self, user_input=None):
        """Handle the initial step - choose between manual and auto-discovery."""
        _LOGGER.info("[Enpal] Config flow started")
        
        if user_input is not None:
            if user_input.get("setup_mode") == "manual":
                return await self.async_step_manual()
            elif user_input.get("setup_mode") == "discover":
                return await self.async_step_discovery()
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("setup_mode", default="discover"): vol.In(
                    get_localized_options(self.hass, "setup_mode")
                ),
            }),
        )

    async def async_step_discovery(self, user_input=None):
        """Handle the discovery step."""
        _LOGGER.info("[Enpal] Starting discovery step")
        
        if not self._discovered_devices and not self._discovery_running:
            # First time - show progress and start discovery
            self._discovery_running = True
            
            # Try quick discovery first
            _LOGGER.info("[Enpal] Starting quick discovery")
            self._discovered_devices = await quick_discover_enpal_devices(self.hass)
            
            # If quick discovery found nothing, try full scan
            if not self._discovered_devices:
                _LOGGER.info("[Enpal] Quick discovery found nothing, starting full scan")
                self._discovered_devices = await discover_enpal_devices(self.hass)
            
            self._discovery_running = False
        
        if user_input is not None:
            selected_url = user_input.get("discovered_device")
            
            if selected_url == "manual":
                # User chose manual setup from discovery results
                return await self.async_step_manual()
            
            if selected_url:
                # User selected a discovered device
                return await self.async_step_configure(user_input={"url": selected_url})
        
        # Show discovery results
        if not self._discovered_devices:
            _LOGGER.warning("[Enpal] No Enpal devices discovered")
            
            return self.async_show_form(
                step_id="discovery",
                data_schema=vol.Schema({
                    vol.Required("discovered_device"): vol.In(
                        get_localized_options(self.hass, "no_devices")
                    ),
                }),
                errors={"base": "no_devices_found"},
                description_placeholders={
                    "discovered_count": "0",
                },
            )
        
        # Create selection dict from discovered devices
        device_options = {url: url for url in self._discovered_devices}
        device_options.update(get_localized_options(self.hass, "discovered_device_none"))
        
        return self.async_show_form(
            step_id="discovery",
            data_schema=vol.Schema({
                vol.Required("discovered_device"): vol.In(device_options)
            }),
            description_placeholders={
                "discovered_count": str(len(self._discovered_devices)),
            },
        )

    async def async_step_manual(self, user_input=None):
        """Handle manual URL entry step."""
        _LOGGER.info("[Enpal] Manual setup step")
        
        if user_input is not None:
            return await self.async_step_configure(user_input)
        
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({
                vol.Required("url", default=DEFAULT_URL): str,
            }),
        )

    async def async_step_configure(self, user_input=None):
        """Handle configuration of interval, groups, and wallbox."""
        _LOGGER.info("[Enpal] Configure step")
        
        # If coming from discovery or manual, we have the URL
        if user_input is not None and "url" in user_input:
            # Validate and store URL
            url_input = user_input["url"]
            url_checked, error = sanitize_url(url_input)
            
            if error or not await validate_enpal_url(self.hass, url_checked):
                errors = {"url": error or "unreachable"}
                return self.async_show_form(
                    step_id="manual",
                    data_schema=vol.Schema({
                        vol.Required("url", default=url_input): str,
                    }),
                    errors=errors,
                )
            
            # Store validated URL for next step
            self._url = url_checked
        
        config = {
            "url": getattr(self, "_url", DEFAULT_URL),
            "interval": DEFAULT_INTERVAL,
            "groups": DEFAULT_GROUPS,
            "use_wallbox_addon": DEFAULT_USE_WALLBOX_ADDON,
        }
        
        if user_input is not None and "interval" in user_input:
            # Final step - validate and create entry
            errors: dict[str, str] = {}
            
            if user_input.get("use_wallbox_addon") and not await validate_wallbox_api(self.hass):
                errors["use_wallbox_addon"] = "wallbox_unreachable"
            
            if not errors:
                # Set unique_id based on URL to prevent duplicate entries
                await self.async_set_unique_id(self._url)
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title="Enpal Webparser",
                    data={"use_options_flow": True},
                    options={
                        "url": self._url,
                        "interval": user_input["interval"],
                        "groups": user_input.get("groups", DEFAULT_GROUPS),
                        "use_wallbox_addon": user_input.get("use_wallbox_addon", False),
                    },
                )
            
            config.update(user_input)
            return self.async_show_form(
                step_id="configure",
                data_schema=vol.Schema({
                    vol.Required("interval", default=config["interval"]): int,
                    vol.Optional("groups", default=config["groups"]): cv.multi_select(DEFAULT_GROUPS),
                    vol.Optional("use_wallbox_addon", default=config["use_wallbox_addon"]): bool,
                }),
                errors=errors,
                description_placeholders={
                    "url": self._url,
                },
            )
        
        return self.async_show_form(
            step_id="configure",
            data_schema=vol.Schema({
                vol.Required("interval", default=config["interval"]): int,
                vol.Optional("groups", default=config["groups"]): cv.multi_select(DEFAULT_GROUPS),
                vol.Optional("use_wallbox_addon", default=config["use_wallbox_addon"]): bool,
            }),
            description_placeholders={
                "url": self._url,
            },
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
