#
# Tests for Enpal Webparser - wallbox_api.py
#
# Verifies that wallbox control actions prefer the native Blazor client and
# fall back to the legacy addon, in both legacy (use_native=False) and
# websocket (use_native=True) modes.
#
# To run: pytest custom_components/enpal_webparser/tests/test_wallbox_api.py
#

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.enpal_webparser.wallbox_api import WallboxApiClient


def _make_client(enpal_base_url, use_native):
    hass = MagicMock()
    return WallboxApiClient(
        hass,
        enpal_base_url=enpal_base_url,
        use_native=use_native,
    )


@pytest.mark.asyncio
async def test_legacy_mode_prefers_blazor_for_control():
    """In legacy mode with a known box URL, control uses Blazor, not the addon."""
    client = _make_client("http://192.168.1.50", use_native=False)

    blazor = AsyncMock()
    blazor.set_mode = AsyncMock(return_value=True)
    client._blazor_client = blazor
    client._ensure_blazor_client = AsyncMock(return_value=True)
    client._post = AsyncMock(return_value=True)

    result = await client.set_mode_eco()

    assert result is True
    blazor.set_mode.assert_awaited_once_with("eco")
    client._post.assert_not_awaited()


@pytest.mark.asyncio
async def test_falls_back_to_addon_when_blazor_unavailable():
    """If the Blazor client cannot connect, the addon endpoint is used."""
    client = _make_client("http://192.168.1.50", use_native=False)

    client._ensure_blazor_client = AsyncMock(return_value=False)
    client._post = AsyncMock(return_value=True)

    result = await client.set_mode_solar()

    assert result is True
    client._post.assert_awaited_once_with("/set_solar")


@pytest.mark.asyncio
async def test_falls_back_to_addon_when_blazor_raises():
    """If the Blazor click raises, the addon endpoint is used as fallback."""
    client = _make_client("http://192.168.1.50", use_native=False)

    blazor = AsyncMock()
    blazor.set_mode = AsyncMock(side_effect=RuntimeError("boom"))
    client._blazor_client = blazor
    client._ensure_blazor_client = AsyncMock(return_value=True)
    client._post = AsyncMock(return_value=True)

    result = await client.set_mode_full()

    assert result is True
    client._post.assert_awaited_once_with("/set_full")


@pytest.mark.asyncio
async def test_no_box_url_uses_addon_only():
    """Without a box URL, Blazor is disabled and only the addon is used."""
    client = _make_client(None, use_native=False)

    client._post = AsyncMock(return_value=True)

    result = await client.start_charging()

    assert result is True
    client._post.assert_awaited_once_with("/start")


@pytest.mark.asyncio
async def test_call_and_refresh_maps_endpoint_and_refreshes():
    """call_and_refresh_sensors maps the endpoint to an action and refreshes."""
    client = _make_client("http://192.168.1.50", use_native=False)
    client.set_mode_eco = AsyncMock(return_value=True)

    hass = client._hass
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    result = await client.call_and_refresh_sensors(
        "/set_eco",
        sensor_entities=["sensor.wallbox_lademodus"],
        wait_time=0,
    )

    assert result is True
    client.set_mode_eco.assert_awaited_once()
    hass.services.async_call.assert_awaited_once()
