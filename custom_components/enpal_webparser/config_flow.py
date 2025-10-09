import logging
import sys
import asyncio
from typing import Any, cast
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector as sel

from .const import (
    DEFAULT_GROUPS,
    DEFAULT_INTERVAL,
    DEFAULT_URL,
    DEFAULT_USE_WALLBOX_ADDON,
    DEFAULT_WALLBOX_API_ENDPOINT,
    DOMAIN,
)
from .ip_discovery import scan_for_enpal_box

_LOGGER = logging.getLogger(__name__)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def is_valid_enpal_url_format(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "http" and bool(parsed.netloc)


def sanitize_url(raw_url: str) -> tuple[str, str | None]:
    url = raw_url.strip()
    if not url.endswith("/deviceMessages"):
        url = url.rstrip("/") + "/deviceMessages"
    if not is_valid_enpal_url_format(url):
        _LOGGER.warning("[Enpal] Invalid URL format: %s", url)
        return url, "invalid_format"
    return url, None


async def validate_enpal_url(hass, url: str) -> bool:
    try:
        session = async_get_clientsession(hass)
        async with session.get(url, timeout=30) as resp:
            return resp.status == 200
    except Exception:
        _LOGGER.warning("[Enpal] URL not reachable: %s", url)
        return False




async def validate_wallbox_api(hass) -> bool:
    url = f"{DEFAULT_WALLBOX_API_ENDPOINT}/status"
    try:
        session = async_get_clientsession(hass)
        async with session.get(url, timeout=45) as resp:
            if resp.status != 200:
                return False
            data = await resp.json()
            return bool(data.get("success"))
    except Exception:
        _LOGGER.warning("[Enpal] Wallbox API not reachable: %s", url)
        return False


def get_default_config(options: dict[str, Any] | None = None) -> dict[str, Any]:
    src = dict(options) if options else {}
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
            vol.Optional("groups", default=cast(Any, config["groups"])): cv.multi_select(
                DEFAULT_GROUPS
            ),
            vol.Optional(
                "use_wallbox_addon", default=cast(Any, config["use_wallbox_addon"])
            ): bool,
        }
    )


async def process_user_input(
    hass, user_input: dict[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, str]]:
    errors: dict[str, str]: dict[str, str] = {}
    url_checked, error = sanitize_url(user_input.get("url", ""))
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
        "interval": user_input.get("interval"),
        "groups": user_input.get("groups", DEFAULT_GROUPS),
        "use_wallbox_addon": user_input.get("use_wallbox_addon", False),
    }, {}


class EnpalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Enpal Webparser."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        return await self.async_step_mode(user_input)

    async def async_step_mode(self, user_input=None):
        """Step: Auswahl zwischen automatischer Suche und manueller IP-Eingabe."""

        # Sprechende Labels (DE/EN); interne Values bleiben neutral
        labels_de = {
            "scan_auto": "Automatische Suche – lokales Netzwerk nach Enpal Box durchsuchen (empfohlen)",
            "manual_ip": "Manuelle IP-Eingabe – Adresse selbst angeben",
        }
        labels_en = {
            "scan_auto": "Automatic discovery – scan the local network for the Enpal Box (recommended)",
            "manual_ip": "Manual IP entry – provide the address yourself",
        }

        # Grobe Spracherkennung (Backend-Systemsprache); funktioniert offline & ohne UI-Session
        lang = (self.hass.config.language or "en").lower()
        lbl = labels_de if lang.startswith("de") else labels_en

        # Bilingualer Beschreibungstext als Fallback, falls das Frontend mal die Sprache mischt
        description = (
            "Automatische Suche füllt die IP automatisch aus; alternativ manuelle IP-Eingabe. / "
            "Automatic discovery prefills the IP; alternatively choose manual IP entry."
        )

        if user_input is None:
            # Mapping: Anzeige-Label -> interner Wert
            options = {
                lbl["scan_auto"]: "scan_auto",
                lbl["manual_ip"]: "manual_ip",
            }
            schema = vol.Schema({
                vol.Required("mode", default="scan_auto"): vol.In(options)
            })
            return self.async_show_form(
                step_id="mode",
                data_schema=schema,
                description_placeholders={"info": description},
                errors={},
            )

        # Ergebnis sicher auswerten: normal kommt der interne Value zurück
        selection = user_input.get("mode")

        # Falls ein älteres Frontend doch das Label zurückgibt, fangen wir das ab:
        if selection in (lbl["manual_ip"], labels_de["manual_ip"], labels_en["manual_ip"]):
            selection = "manual_ip"
        if selection in (lbl["scan_auto"], labels_de["scan_auto"], labels_en["scan_auto"]):
            selection = "scan_auto"

        if selection == "manual_ip":
            return await self.async_step_manual()
        return await self.async_step_discovery()


    async def async_step_discovery(self, user_input=None):
        _LOGGER.debug("[Enpal] Starting automatic discovery")
        found = await scan_for_enpal_box()
        self.context["discovered_url"] = (
            f"http://{found[0]}/deviceMessages" if found else DEFAULT_URL
        )
        return await self.async_step_manual()

    async def async_step_manual(self, user_input=None):
        config = get_default_config()
        if "discovered_url" in self.context:
            config["url"]: dict[str, str] = self.context["discovered_url"]

        errors: dict[str, str] = {}
        if user_input is not None:
            result, errors = await process_user_input(self.hass, user_input)
            if result:
                return self.async_create_entry(
                    title="Enpal Webparser", data={"use_options_flow": True}, options=result
                )
            config.update(user_input)

        return self.async_show_form(
            step_id="manual", data_schema=get_form_schema(config), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EnpalOptionsFlowHandler(config_entry)


class EnpalOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for Enpal Webparser."""

    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        config = get_default_config(dict(self._config_entry.options))
        errors: dict[str, str]: dict[str, str] = {}

        if user_input is not None:
            result, errors = await process_user_input(self.hass, user_input)
            if result:
                return self.async_create_entry(title="", data=result)
            config.update(user_input)

        return self.async_show_form(
            step_id="init", data_schema=get_form_schema(config), errors=errors
        )