#
# Tests for Enpal Webparser - devices.py
#
# Unit tests for the device layout (Enpal Box + sub-devices via via_device),
# the config entry title migration and the one-time area inheritance.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
#
# To run: pytest custom_components/enpal_webparser/tests/test_devices.py
#

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from custom_components.enpal_webparser.const import DOMAIN
from custom_components.enpal_webparser.devices import (
    MAIN_DEVICE_ID,
    MAIN_DEVICE_NAME,
    SUB_DEVICE_GROUPS,
    EnpalDeviceEntity,
    async_setup_devices,
    device_info_for_group,
)


@pytest.mark.parametrize("group", [None, "", "Site Data", "IoTEdgeDevice", "ControlBox", "Unknown"])
def test_box_groups_use_main_device(group):
    info = device_info_for_group(group)
    assert info["identifiers"] == {(DOMAIN, MAIN_DEVICE_ID)}
    assert info["name"] == MAIN_DEVICE_NAME
    assert info["manufacturer"] == "Enpal"
    assert "via_device" not in info


@pytest.mark.parametrize("group,key", list(SUB_DEVICE_GROUPS.items()))
def test_product_groups_use_sub_device(group, key):
    info = device_info_for_group(group)
    assert info["identifiers"] == {(DOMAIN, f"{MAIN_DEVICE_ID}_{key}")}
    assert info["translation_key"] == key
    assert info["via_device"] == (DOMAIN, MAIN_DEVICE_ID)
    # Sub-devices are named via translations, not a hard-coded name.
    assert "name" not in info


def test_via_device_id_used_when_supported():
    """HA 2026.8+: link sub-devices by registry id instead of identifier."""
    with patch("custom_components.enpal_webparser.devices.SUPPORTS_VIA_DEVICE_ID", True):
        info = device_info_for_group("Wallbox", "box-registry-id")
    assert info["via_device_id"] == "box-registry-id"
    assert "via_device" not in info


def test_via_device_fallback_on_older_home_assistant():
    """Before HA 2026.8 DeviceInfo has no via_device_id key."""
    with patch("custom_components.enpal_webparser.devices.SUPPORTS_VIA_DEVICE_ID", False):
        info = device_info_for_group("Wallbox", "box-registry-id")
    assert info["via_device"] == (DOMAIN, MAIN_DEVICE_ID)
    assert "via_device_id" not in info


class _WallboxEntity(EnpalDeviceEntity):
    _enpal_group = "Wallbox"


def test_entity_mixin_uses_main_device_id_from_entry_data():
    entity = _WallboxEntity()
    entity.hass = MagicMock()
    entity.hass.data = {DOMAIN: {"entry1": {"main_device_id": "box-registry-id"}}}
    entity.platform = SimpleNamespace(config_entry=SimpleNamespace(entry_id="entry1"))
    with patch("custom_components.enpal_webparser.devices.SUPPORTS_VIA_DEVICE_ID", True):
        info = entity.device_info
    assert info["identifiers"] == {(DOMAIN, f"{MAIN_DEVICE_ID}_wallbox")}
    assert info["via_device_id"] == "box-registry-id"


def test_entity_mixin_without_platform_falls_back():
    """Before the entity is added there is no hass/platform yet."""
    info = _WallboxEntity().device_info
    assert info["via_device"] == (DOMAIN, MAIN_DEVICE_ID)


def test_sub_device_translations_exist():
    translations = Path(__file__).parent.parent / "translations"
    for lang in ("de", "en"):
        devices = json.loads((translations / f"{lang}.json").read_text(encoding="utf-8"))["device"]
        for key in SUB_DEVICE_GROUPS.values():
            assert devices[key]["name"], f"missing {lang} device name for {key}"


def _setup(title="Enpal Box", main_area="area_boiler"):
    """Run async_setup_devices against a mocked hass/device registry.

    Returns (hass, entry, registry, devices, listener).
    """
    main = SimpleNamespace(id="main", area_id=main_area, identifiers={(DOMAIN, MAIN_DEVICE_ID)})
    devices = {"main": main}

    registry = MagicMock()
    registry.async_get_or_create.return_value = main
    registry.async_get.side_effect = devices.get

    hass = MagicMock()
    entry = MagicMock()
    entry.title = title
    entry.entry_id = "entry1"

    with patch(
        "custom_components.enpal_webparser.devices.dr.async_get", return_value=registry
    ):
        assert async_setup_devices(hass, entry) == "main"

    listener = hass.bus.async_listen.call_args[0][1]
    return hass, entry, registry, devices, listener


def _event(action, device_id):
    return SimpleNamespace(data={"action": action, "device_id": device_id})


def test_main_device_registered_before_platforms():
    _, entry, registry, _, _ = _setup()
    kwargs = registry.async_get_or_create.call_args.kwargs
    assert kwargs["config_entry_id"] == "entry1"
    assert kwargs["identifiers"] == {(DOMAIN, MAIN_DEVICE_ID)}
    assert kwargs["name"] == MAIN_DEVICE_NAME
    entry.async_on_unload.assert_called_once()


def test_legacy_entry_title_is_renamed():
    hass, entry, _, _, _ = _setup(title="Enpal Webparser")
    hass.config_entries.async_update_entry.assert_called_once_with(entry, title=MAIN_DEVICE_NAME)


def test_custom_entry_title_is_kept():
    hass, _, _, _, _ = _setup(title="Meine Solaranlage")
    hass.config_entries.async_update_entry.assert_not_called()


def test_new_sub_device_inherits_box_area():
    _, _, registry, devices, listener = _setup()
    devices["inv"] = SimpleNamespace(
        id="inv",
        area_id=None,
        via_device_id="main",
        identifiers={(DOMAIN, f"{MAIN_DEVICE_ID}_inverter")},
    )
    listener(_event("create", "inv"))
    registry.async_update_device.assert_called_once_with("inv", area_id="area_boiler")


@pytest.mark.parametrize(
    "action,area_id,via_device_id,identifier,main_area",
    [
        ("update", None, "main", f"{MAIN_DEVICE_ID}_inverter", "area_boiler"),  # not a new device
        ("create", "garage", "main", f"{MAIN_DEVICE_ID}_wallbox", "area_boiler"),  # already has an area
        ("create", None, "other", f"{MAIN_DEVICE_ID}_wallbox", "area_boiler"),  # not behind the box
        ("create", None, "main", "some_other_device", "area_boiler"),  # not one of ours
        ("create", None, "main", f"{MAIN_DEVICE_ID}_battery", None),  # box has no area
    ],
)
def test_area_not_touched(action, area_id, via_device_id, identifier, main_area):
    _, _, registry, devices, listener = _setup(main_area=main_area)
    devices["dev"] = SimpleNamespace(
        id="dev",
        area_id=area_id,
        via_device_id=via_device_id,
        identifiers={(DOMAIN, identifier)},
    )
    listener(_event(action, "dev"))
    registry.async_update_device.assert_not_called()
