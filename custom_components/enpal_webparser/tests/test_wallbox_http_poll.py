"""Tests for wallbox data fetching — proves that:

1. Plain HTTP GET to /wallbox returns NO pre-rendered data (Blazor Server
   only sends the empty shell; actual data is delivered via SignalR
   WebSocket RenderBatch).
2. The _extract_status_text parser correctly extracts Mode/Status from
   RenderBatch binary data.
3. The new _request_status_refresh / get_wallbox_data flow uses WebSocket
   reconnect instead of the broken HTTP approach.
"""
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.enpal_webparser.api.wallbox_client import WallboxBlazorClient


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "wallbox.html"


def _parse_html_fixture() -> tuple:
    """Feed the real wallbox.html through the status parser."""
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    return WallboxBlazorClient._extract_status_text(html.encode("utf-8"))


# ------------------------------------------------------------------
# HTTP GET returns nothing (proves the old approach was broken)
# ------------------------------------------------------------------

def test_http_get_returns_no_mode():
    """HTTP GET /wallbox does not contain any pre-rendered Mode value."""
    mode, _status = _parse_html_fixture()
    assert mode is None, f"Expected mode=None from HTTP GET, got '{mode}'"


def test_http_get_returns_no_status():
    """HTTP GET /wallbox does not contain any pre-rendered Status value."""
    _mode, status = _parse_html_fixture()
    assert status is None, f"Expected status=None from HTTP GET, got '{status}'"


# ------------------------------------------------------------------
# WebSocket RenderBatch parsing works correctly
# ------------------------------------------------------------------

def test_extract_status_from_render_batch():
    """Binary RenderBatch data with embedded 'Mode Eco' / 'Status Charging'
    IS correctly parsed — proving the WebSocket path works while HTTP doesn't."""
    # Simulate binary data that would come from a Blazor RenderBatch
    fake_batch = b"\x00\x00Mode Eco\x00\x00Status Charging\x00\x00"
    mode, status = WallboxBlazorClient._extract_status_text(fake_batch)
    assert mode == "Eco"
    assert status == "Charging"


def test_extract_status_all_valid_modes():
    """All valid modes are correctly extracted from binary data."""
    for mode_name in ("Eco", "Solar", "Full", "Smart", "Fast"):
        data = f"...Mode {mode_name}...Status Connected...".encode("utf-8")
        mode, status = WallboxBlazorClient._extract_status_text(data)
        assert mode == mode_name, f"Failed for mode '{mode_name}'"
        assert status == "Connected"


def test_html_contains_only_heading():
    """The Blazor shell contains only the Wallbox heading, no data."""
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    assert '<h1 class="m-3">Wallbox</h1>' in html
    # No mode/status keywords in the pre-rendered HTML
    assert "Mode Eco" not in html
    assert "Mode Solar" not in html
    assert "Mode Full" not in html
    assert "Status Charging" not in html
    assert "Status Connected" not in html


# ------------------------------------------------------------------
# New WebSocket-based polling flow
# ------------------------------------------------------------------

def test_client_has_connection_lock():
    """BlazorClient has an asyncio.Lock for serializing poll/click."""
    client = WallboxBlazorClient("http://192.168.2.70")
    assert isinstance(client._connection_lock, asyncio.Lock)


def test_client_has_render_event():
    """BlazorClient has a _render_event for RenderBatch signalling."""
    client = WallboxBlazorClient("http://192.168.2.70")
    assert isinstance(client._render_event, asyncio.Event)


def test_process_render_batch_sets_render_event():
    """_process_render_batch sets _render_event on any RenderBatch."""
    client = WallboxBlazorClient("http://192.168.2.70")
    assert not client._render_event.is_set()

    # Feed a fake RenderBatch with mode/status — event should fire
    fake_batch = b"\x00Mode Solar\x00Status Connected\x00"
    client._process_render_batch(fake_batch)
    assert client._render_event.is_set()
    assert client._mode == "Solar"
    assert client._status == "Connected"


def test_process_render_batch_sets_render_event_even_without_data():
    """_render_event fires even if the RenderBatch has no mode/status."""
    client = WallboxBlazorClient("http://192.168.2.70")
    assert not client._render_event.is_set()

    # Feed a minimal RenderBatch without any parseable content
    client._process_render_batch(b"\x00\x00\x00\x00")
    assert client._render_event.is_set()


def test_request_status_refresh_returns_false_when_disconnected():
    """_request_status_refresh returns False when not connected."""
    client = WallboxBlazorClient("http://192.168.2.70")
    client.connected = False
    result = asyncio.get_event_loop().run_until_complete(
        client._request_status_refresh()
    )
    assert result is False


def test_get_wallbox_data_returns_cached_on_connect_failure():
    """get_wallbox_data returns cached values when reconnect fails."""
    client = WallboxBlazorClient("http://192.168.2.70")
    client._mode = "Eco"
    client._status = "Connected"
    client.connected = False

    with patch.object(client, 'connect', new_callable=AsyncMock, return_value=False):
        result = asyncio.get_event_loop().run_until_complete(
            client.get_wallbox_data()
        )

    assert result is not None
    assert result["mode"] == "eco"
    assert result["status"] == "connected"
    assert result["success"] is True


def test_get_wallbox_data_returns_none_without_cache():
    """get_wallbox_data returns None when no cached data and connect fails."""
    client = WallboxBlazorClient("http://192.168.2.70")
    client._mode = None
    client._status = None
    client.connected = False

    with patch.object(client, 'connect', new_callable=AsyncMock, return_value=False):
        result = asyncio.get_event_loop().run_until_complete(
            client.get_wallbox_data()
        )

    assert result is None


def test_get_wallbox_data_calls_connect_when_disconnected():
    """get_wallbox_data connects when no live WebSocket exists."""
    client = WallboxBlazorClient("http://192.168.2.70")
    client.connected = False

    async def fake_connect():
        client._mode = "Full"
        client._status = "Charging"
        client.connected = True
        return True

    with patch.object(client, 'connect', side_effect=fake_connect):
        result = asyncio.get_event_loop().run_until_complete(
            client.get_wallbox_data()
        )

    assert result["mode"] == "full"
    assert result["status"] == "charging"


def test_get_wallbox_data_tries_refresh_when_connected():
    """get_wallbox_data tries lightweight refresh when already connected."""
    client = WallboxBlazorClient("http://192.168.2.70")
    client.connected = True
    client.ws = MagicMock()
    client.ws.closed = False
    client._mode = "Eco"
    client._status = "Connected"

    with patch.object(client, '_request_status_refresh',
                      new_callable=AsyncMock, return_value=True):
        result = asyncio.get_event_loop().run_until_complete(
            client.get_wallbox_data()
        )

    assert result["mode"] == "eco"
    assert result["status"] == "connected"


def test_get_wallbox_data_falls_back_to_reconnect_on_refresh_failure():
    """get_wallbox_data reconnects when lightweight refresh fails."""
    client = WallboxBlazorClient("http://192.168.2.70")
    client.connected = True
    client.ws = MagicMock()
    client.ws.closed = False
    client._mode = "Eco"
    client._status = "Connected"

    async def fake_connect():
        client._mode = "Solar"
        client._status = "Charging"
        client.connected = True
        return True

    with patch.object(client, '_request_status_refresh',
                      new_callable=AsyncMock, return_value=False), \
         patch.object(client, 'connect', side_effect=fake_connect):
        result = asyncio.get_event_loop().run_until_complete(
            client.get_wallbox_data()
        )

    # Should have the reconnected values, not the old cached ones
    assert result["mode"] == "solar"
    assert result["status"] == "charging"
