# pyright: reportIncompatibleVariableOverride=false
#
# Home Assistant Custom Component: Enpal Webparser
#
# File: repairs.py
#
# Description:
#   Repair flows for the Enpal Webparser integration. Currently handles the
#   case where wallbox control is enabled but no matching "Wallbox Status"
#   source sensor could be auto-detected (e.g. firmware naming variants). The
#   flow lets the user pick the correct raw Wallbox sensor and stores it in the
#   ``wallbox_status_source`` option.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
# Repository:   https://github.com/derolli1976/enpal
#

import logging
from typing import Any

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant

from .config_flow import get_wallbox_source_options
from .const import DEFAULT_URL

_LOGGER = logging.getLogger(__name__)


class WallboxStatusSourceRepairFlow(RepairsFlow):
    """Let the user select the raw Wallbox status sensor."""

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        return await self.async_step_select()

    async def async_step_select(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry is None:
            return self.async_abort(reason="entry_not_found")

        if user_input is not None:
            options = dict(entry.options)
            options["wallbox_status_source"] = user_input["wallbox_status_source"]
            self.hass.config_entries.async_update_entry(entry, options=options)
            _LOGGER.info(
                "[Enpal] Wallbox status source set to %s via repair flow",
                user_input["wallbox_status_source"],
            )
            # The update listener reloads the entry; sensor.py then re-evaluates
            # the source and deletes the issue if it now resolves.
            return self.async_create_entry(title="", data={})

        url = entry.options.get("url", DEFAULT_URL)
        sources = await get_wallbox_source_options(self.hass, url)

        schema = vol.Schema(
            {
                vol.Required(
                    "wallbox_status_source",
                    default=entry.options.get("wallbox_status_source", "auto"),
                ): vol.In(sources)
            }
        )
        return self.async_show_form(step_id="select", data_schema=schema)


class HtmlModeUnsupportedRepairFlow(RepairsFlow):
    """Switch the data source from HTML to WebSocket with one confirmation.

    Raised when the entry is fixed to HTML mode but the box runs firmware
    8.51+, where the /deviceMessages page no longer contains the device data.
    """

    def __init__(self, entry_id: str, firmware_version: str) -> None:
        self._entry_id = entry_id
        self._firmware_version = firmware_version

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry is None:
            return self.async_abort(reason="entry_not_found")

        if user_input is not None:
            options = dict(entry.options)
            options["data_source"] = "websocket"
            self.hass.config_entries.async_update_entry(entry, options=options)
            _LOGGER.info(
                "[Enpal] Data source switched to websocket via repair flow "
                "(firmware %s)",
                self._firmware_version,
            )
            # The update listener reloads the entry; sensor.py deletes the
            # issue when it sets up in WebSocket mode.
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"firmware_version": self._firmware_version},
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> RepairsFlow:
    """Create the repair flow for an Enpal issue."""
    entry_id = (data or {}).get("entry_id", "")
    if issue_id.startswith("html_mode_unsupported_firmware"):
        firmware_version = (data or {}).get("firmware_version", "?")
        return HtmlModeUnsupportedRepairFlow(entry_id, firmware_version)
    return WallboxStatusSourceRepairFlow(entry_id)
