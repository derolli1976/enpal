#
# Home Assistant Custom Component: Enpal Webparser
#
# File: devices.py
#
# Description:
#   Device registry layout for the Enpal Box integration.
#   The Enpal Box is the main device. Inverter, battery, wallbox, heat pump
#   and power sensor are separate products reached through the box, so each
#   one gets its own device linked to the box via ``via_device`` (issue #192).
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
# Repository:   https://github.com/derolli1976/enpal
#
# Compatible with Home Assistant Core 2024.3 and later (device name translations).
#
# See README.md for setup and usage instructions.
#

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Identifier of the main device. Kept from the original single-device layout
# so the device id and its area survive the split. Note: actions targeting
# the main device by device_id no longer reach entities that moved to a
# sub-device (via_device does not propagate targets like child devices do).
MAIN_DEVICE_ID = "enpal_device"
MAIN_DEVICE_NAME = "Enpal Box"

# Config entry title used before the rename to "Enpal Box".
LEGACY_ENTRY_TITLE = "Enpal Webparser"

# Sensor groups that represent a product of their own behind the Enpal Box,
# mapped to their device translation key. All other groups (Site Data,
# IoTEdgeDevice, ControlBox, ...) describe the box itself and stay on the
# main device.
GROUP_INVERTER = "Inverter"
GROUP_WALLBOX = "Wallbox"

SUB_DEVICE_GROUPS = {
    GROUP_INVERTER: "inverter",
    "Battery": "battery",
    GROUP_WALLBOX: "wallbox",
    "Heatpump": "heatpump",
    "PowerSensor": "power_sensor",
}


def main_device_info() -> DeviceInfo:
    """Return the device info of the Enpal Box itself."""
    return DeviceInfo(
        identifiers={(DOMAIN, MAIN_DEVICE_ID)},
        name=MAIN_DEVICE_NAME,
        manufacturer="Enpal",
        # The box exposes no model designation. Explicitly None (instead of
        # omitting the key) so the registry drops the legacy "Webparser".
        model=None,
    )


def device_info_for_group(group: str | None) -> DeviceInfo:
    """Return the device info for entities of the given sensor group."""
    key = SUB_DEVICE_GROUPS.get(group or "")
    if key is None:
        return main_device_info()
    return DeviceInfo(
        identifiers={(DOMAIN, f"{MAIN_DEVICE_ID}_{key}")},
        translation_key=key,
        via_device=(DOMAIN, MAIN_DEVICE_ID),
    )


def _sub_device_identifiers() -> set[tuple[str, str]]:
    return {(DOMAIN, f"{MAIN_DEVICE_ID}_{key}") for key in SUB_DEVICE_GROUPS.values()}


@callback
def async_setup_devices(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register the main device and let new sub-devices inherit its area.

    The main device is registered before the platforms are set up so that the
    ``via_device`` reference of the sub-devices always resolves.

    Before the split all entities lived on the main device and followed its
    area. A sub-device that is created for the first time (e.g. right after
    updating) copies the area of the Enpal Box once, so entities without an
    area of their own do not suddenly lose it. Later area changes by the user
    are left alone.
    """
    if entry.title == LEGACY_ENTRY_TITLE:
        _LOGGER.info("[Enpal] Renaming config entry title to '%s'", MAIN_DEVICE_NAME)
        hass.config_entries.async_update_entry(entry, title=MAIN_DEVICE_NAME)

    device_registry = dr.async_get(hass)
    main_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id, **main_device_info()
    )
    sub_identifiers = _sub_device_identifiers()

    @callback
    def _async_inherit_area(event: Event) -> None:
        if event.data["action"] != "create":
            return
        device = device_registry.async_get(event.data["device_id"])
        if device is None or device.area_id or not device.identifiers & sub_identifiers:
            return
        parent = device_registry.async_get(main_device.id)
        if parent is None or parent.area_id is None:
            return
        _LOGGER.info(
            "[Enpal] Assigning area '%s' of the Enpal Box to new device %s",
            parent.area_id,
            device.id,
        )
        device_registry.async_update_device(device.id, area_id=parent.area_id)

    entry.async_on_unload(
        hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, _async_inherit_area)
    )
