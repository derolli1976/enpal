"""Regression tests for failed setup, retry, cancellation, and unloading."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed

import custom_components.enpal_webparser as integration
from custom_components.enpal_webparser import sensor
from custom_components.enpal_webparser.const import DOMAIN


@pytest.fixture
def runtime(monkeypatch):
    """Keep platform registration and client ownership visible to the tests."""
    state = SimpleNamespace(events=[], clients=[], coordinators=[], entities=[])
    state.fail_connect = False
    state.fail_forward = None
    state.entry = SimpleNamespace(
        entry_id="test-entry",
        data={},
        options={
            "url": "http://enpal.test/deviceMessages",
            "data_source": "websocket",
            "interval": 60,
            "groups": ["Wallbox"],
            "use_wallbox": True,
        },
        async_on_unload=Mock(),
        add_update_listener=Mock(return_value=Mock()),
    )
    state.hass = SimpleNamespace(data={})

    class Client:
        def __init__(self, *args, **kwargs):
            self.connected = False
            self.closed = False
            self.callback = None
            state.clients.append(self)

        async def connect(self):
            state.events.append("connect")
            self.connected = not state.fail_connect
            return self.connected

        def is_connected(self):
            return self.connected

        async def fetch_data(self):
            state.events.append("fetch")
            return {
                "sensors": [{"name": "wallbox_energy", "value": 100.0}],
                "source": "websocket",
            }

        async def close(self):
            state.events.append("close")
            self.closed = True
            self.connected = False

        def set_data_callback(self, callback):
            self.callback = callback

    class Coordinator:
        def __init__(self, hass, logger, *, name, update_method, update_interval):
            self.update_method = update_method
            self.data = None
            self.stopped = False
            state.coordinators.append(self)

        async def async_config_entry_first_refresh(self):
            try:
                self.data = await self.update_method()
            except UpdateFailed as err:
                raise ConfigEntryNotReady(str(err)) from err

        async def async_shutdown(self):
            state.events.append("shutdown")
            self.stopped = True

        def async_add_listener(self, callback):
            return Mock()

        def async_update_listeners(self):
            pass

    async def forward(entry, platforms):
        state.events.append("forward")
        if state.fail_forward is not None:
            raise state.fail_forward
        await sensor.async_setup_entry(state.hass, entry, state.entities.extend)

    async def unload(entry, platforms):
        state.events.append("unload")
        return True

    state.hass.config_entries = SimpleNamespace(
        async_forward_entry_setups=AsyncMock(side_effect=forward),
        async_unload_platforms=AsyncMock(side_effect=unload),
        async_update_entry=Mock(),
        async_reload=AsyncMock(),
    )
    state.new_client = Client
    monkeypatch.setattr(integration, "async_setup_devices", Mock(return_value="device"))
    monkeypatch.setattr(integration, "WallboxApiClient", Client)
    monkeypatch.setattr(sensor, "EnpalWebSocketClient", Client)
    monkeypatch.setattr(sensor, "DataUpdateCoordinator", Coordinator)
    monkeypatch.setattr(sensor.ir, "async_delete_issue", Mock())
    monkeypatch.setattr(sensor, "_find_wallbox_source", Mock(return_value="wallbox_energy"))
    monkeypatch.setattr(sensor, "_manage_wallbox_status_issue", Mock())
    monkeypatch.setattr(
        sensor, "build_sensor_entity",
        lambda data, coordinator, **kwargs: (data["name"], coordinator),
    )
    for name in (
        "CumulativeEnergySensor", "DailyResetFromEntitySensor",
        "WallboxNativeModeSensor", "WallboxNativeStatusSensor",
    ):
        monkeypatch.setattr(sensor, name, Mock())
    return state


@pytest.mark.asyncio
async def test_connection_failure_does_not_register_platforms(runtime):
    runtime.fail_connect = True
    with pytest.raises(ConfigEntryNotReady):
        await integration.async_setup_entry(runtime.hass, runtime.entry)

    runtime.hass.config_entries.async_forward_entry_setups.assert_not_awaited()
    assert all(client.closed for client in runtime.clients)
    assert all(coordinator.stopped for coordinator in runtime.coordinators)
    assert runtime.entry.entry_id not in runtime.hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_first_fetch_precedes_platform_registration(runtime):
    assert await integration.async_setup_entry(runtime.hass, runtime.entry)
    assert runtime.events.index("fetch") < runtime.events.index("forward")
    assert runtime.events.count("fetch") == 1
    assert runtime.events.count("connect") == 1
    coordinator = runtime.hass.data[DOMAIN][runtime.entry.entry_id]["coordinator"]
    assert runtime.entities[0] == ("wallbox_energy", coordinator)


@pytest.mark.asyncio
async def test_partial_platform_failure_unloads_and_closes(runtime):
    runtime.fail_forward = RuntimeError("platform setup failed")
    with pytest.raises(RuntimeError, match="platform setup failed"):
        await integration.async_setup_entry(runtime.hass, runtime.entry)

    runtime.hass.config_entries.async_unload_platforms.assert_awaited_once()
    assert all(client.closed for client in runtime.clients)
    assert all(coordinator.stopped for coordinator in runtime.coordinators)


@pytest.mark.asyncio
async def test_cancelled_setup_unloads_and_preserves_cancellation(runtime):
    runtime.fail_forward = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await integration.async_setup_entry(runtime.hass, runtime.entry)

    runtime.hass.config_entries.async_unload_platforms.assert_awaited_once()
    assert all(client.closed for client in runtime.clients)
    assert all(coordinator.stopped for coordinator in runtime.coordinators)


@pytest.mark.asyncio
async def test_successful_retry_after_connection_failure(runtime):
    runtime.fail_connect = True
    with pytest.raises(ConfigEntryNotReady):
        await integration.async_setup_entry(runtime.hass, runtime.entry)
    runtime.fail_connect = False

    assert await integration.async_setup_entry(runtime.hass, runtime.entry)
    coordinator = runtime.hass.data[DOMAIN][runtime.entry.entry_id]["coordinator"]
    assert coordinator.data


@pytest.mark.asyncio
async def test_unload_stops_polling_before_closing_clients(runtime):
    await integration.async_setup_entry(runtime.hass, runtime.entry)
    runtime.events.clear()
    energy_state = runtime.hass.data[DOMAIN]["cumulative_energy_state"]

    assert await integration.async_unload_entry(runtime.hass, runtime.entry)
    assert runtime.events.index("unload") < runtime.events.index("shutdown")
    assert runtime.events.index("shutdown") < runtime.events.index("close")
    assert runtime.entry.entry_id not in runtime.hass.data[DOMAIN]
    assert "coordinator" not in runtime.hass.data[DOMAIN]
    assert runtime.hass.data[DOMAIN]["cumulative_energy_state"] is energy_state


@pytest.mark.asyncio
async def test_failed_unload_leaves_running_clients_available(runtime):
    await integration.async_setup_entry(runtime.hass, runtime.entry)
    runtime.hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

    assert not await integration.async_unload_entry(runtime.hass, runtime.entry)
    assert all(not client.closed for client in runtime.clients)
    assert all(not coordinator.stopped for coordinator in runtime.coordinators)


@pytest.mark.asyncio
async def test_unload_does_not_close_another_entry(runtime):
    await integration.async_setup_entry(runtime.hass, runtime.entry)
    other_client = runtime.new_client()
    other_coordinator = SimpleNamespace(async_shutdown=AsyncMock())
    domain_data = runtime.hass.data[DOMAIN]
    domain_data["another-entry"] = {
        "api_client": other_client, "coordinator": other_coordinator,
    }
    domain_data["coordinator"] = other_coordinator

    assert await integration.async_unload_entry(runtime.hass, runtime.entry)
    assert not other_client.closed
    other_coordinator.async_shutdown.assert_not_awaited()
    assert domain_data["coordinator"] is other_coordinator
    assert "another-entry" in domain_data
