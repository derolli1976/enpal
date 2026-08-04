"""WebSocket client for Enpal Box using Blazor SignalR protocol.

Connects to /deviceMessages via WebSocket. The Blazor server sends
JS.RenderBatch messages every ~5 s when sensor data changes.

Each RenderBatch already carries the changed sensor rows in its binary
payload, so we parse those incrementally (see :mod:`.render_batch`) and patch
a cached baseline instead of HTTP re-scraping the whole page on every push.
The coordinator still performs a full HTML scrape on its normal poll interval,
which refreshes the baseline and corrects anything the fast path skips
(ambiguous keys, new sensors, oversized values).  Worst case therefore
degrades gracefully to plain interval polling.
"""

import aiohttp
import asyncio
import json
import logging
import time
from collections import deque
from typing import Awaitable, Callable, Deque, Dict, List, Optional

from .base import EnpalApiClient
from .protocol import (
    ComponentDescriptor,
    extract_blazor_components,
    extract_application_state,
    encode_message,
    decode_messages,
)
from .render_batch import (
    parse_render_batch_strings,
    extract_changed_rows,
    extract_event_handlers,
    is_patchable_value,
)

_LOGGER = logging.getLogger(__name__)

# Minimum seconds between coordinator push notifications triggered by a
# RenderBatch. Incremental diffs are cheap, but pushing tells HA to write all
# entity states, so we still debounce slightly.
_PUSH_DEBOUNCE_SECONDS = 2

# Device classes whose sensor state must be numeric. The fast path refuses to
# write a non-numeric value into these, so a misread RenderBatch row (e.g. a
# timestamp-only update where the value string is absent) cannot turn an energy
# counter "unavailable".
_NUMERIC_DEVICE_CLASSES = frozenset({
    "energy", "power", "voltage", "current", "temperature",
    "frequency", "battery", "humidity", "pressure",
})

# JS calls whose .NET caller deserialises the result into a value type or
# dereferences it. Answering those with null raises inside the circuit and the
# box tears the connection down, so they get a plausible literal instead.
_JS_CALL_RESULTS = {
    "mudpopoverHelper.countProviders": "1",
    "Radzen.createChart": '{"left":0,"top":0,"width":800,"height":400}',
    "Radzen.createResizable": '{"left":0,"top":0,"width":800,"height":400}',
}

# Full string-table dumps of large RenderBatches, for protocol analysis.
_BATCH_DUMP_LIMIT = 3
_BATCH_DUMP_MIN_BYTES = 5000
_BATCH_DUMP_MAX_CHARS = 4000

# Firmware 8.51 hides some rows (e.g. Energy.Battery.Charge.Level) behind
# per-card "Show unsupported values" / "Show internal values" checkboxes.
# Those are circuit state, so our own circuit must switch them on to receive
# the hidden rows. The DOM id suffix is the group name (showInternal_Battery).
_TOGGLE_ID_PREFIXES = ("showUnsupported_", "showInternal_")


class EnpalWebSocketClient(EnpalApiClient):
    """WebSocket client for the /deviceMessages Blazor page.

    The WebSocket connection keeps the Blazor circuit alive so the server
    continuously pushes RenderBatch updates (~every 5 s).  Actual sensor
    data is obtained by HTTP-scraping /deviceMessages with the well-tested
    HTML parser from ``utils.py``.
    """

    # Keep-alive ping interval (seconds) — matches Blazor Server expectation
    _PING_INTERVAL = 15

    def __init__(self, base_url: str, groups: List[str] = None):
        self.base_url = base_url.rstrip('/')
        self.groups = groups or [
            'Battery', 'Inverter', 'IoTEdgeDevice',
            'PowerSensor', 'Wallbox', 'Site Data', 'Heatpump',
        ]
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.components: List[ComponentDescriptor] = []
        self.application_state: str = ""
        self.connected: bool = False
        self._read_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._data_callback: Optional[Callable[[Dict], Awaitable[None]]] = None
        self._last_push_time: float = 0
        self._last_activity: float = 0  # Last message received from server
        # Cached full sensor list + index for incremental RenderBatch patching
        self._baseline: Optional[List[Dict]] = None
        self._key_index: Dict[str, List[int]] = {}
        self._circuit_started: float = 0  # monotonic time of the last StartCircuit
        self._recent_targets: Deque[str] = deque(maxlen=10)
        self._batches_dumped: int = 0
        # "Show unsupported/internal values" checkboxes (firmware 8.51)
        self._toggle_handlers: Dict[str, int] = {}   # dom id -> event handler id
        self._toggles_attempted: Dict[str, int] = {}  # dom id -> handler id last clicked
        self._pending_toggle_calls: Dict[int, str] = {}  # dotnet call id -> dom id
        self._renderer_interop_id: int = 1  # DotNet object ref for DispatchEventAsync
        self._dotnet_call_counter: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Establish WebSocket connection to /deviceMessages."""
        # Clean up any previous connection before reconnecting
        await self._cleanup()

        try:
            _LOGGER.info("[Enpal WebSocket] Connecting to %s/deviceMessages", self.base_url)

            # 1. HTTP session with shared cookie jar
            self.session = aiohttp.ClientSession(
                cookie_jar=aiohttp.CookieJar(),
                connector=aiohttp.TCPConnector(use_dns_cache=False),
            )

            # 2. Load /deviceMessages and extract Blazor bootstrap data
            async with self.session.get(f"{self.base_url}/deviceMessages") as resp:
                if resp.status != 200:
                    raise ValueError(f"HTTP {resp.status} loading /deviceMessages")
                html = await resp.text()
                self.components = extract_blazor_components(html)
                self.application_state = extract_application_state(html)

            if not self.components:
                raise ValueError("No Blazor components found in HTML")
            if not self.application_state:
                raise ValueError("No application state found in HTML")

            _LOGGER.debug("[Enpal WebSocket] Found %d Blazor components", len(self.components))

            # 3. Negotiate SignalR connection
            async with self.session.post(
                f"{self.base_url}/_blazor/negotiate?negotiateVersion=1",
                data="",
            ) as resp:
                if resp.status != 200:
                    raise ValueError(f"HTTP {resp.status} during negotiate")
                negotiate_data = await resp.json()
                connection_token = negotiate_data.get('connectionToken')
                if not connection_token:
                    raise ValueError("No connectionToken in negotiate response")

            # 4. Open WebSocket
            host = self.base_url.replace('http://', '').replace('https://', '')
            ws_url = f"ws://{host}/_blazor?id={connection_token}"
            _LOGGER.debug("[Enpal WebSocket] WS URL: %s", ws_url)
            self.ws = await self.session.ws_connect(ws_url)

            # 5. Blazor handshake
            await self.ws.send_str('{"protocol":"blazorpack","version":1}\x1e')
            msg = await self.ws.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                hs = msg.data.rstrip('\x1e')
            elif msg.type == aiohttp.WSMsgType.BINARY:
                hs = msg.data.decode('utf-8').rstrip('\x1e')
            else:
                raise ValueError(f"Unexpected handshake response type: {msg.type}")
            if '"error"' in hs:
                raise ValueError(f"Handshake error: {hs}")
            _LOGGER.debug("[Enpal WebSocket] Handshake OK: %s", hs)

            # 6. Background read loop
            self._read_task = asyncio.create_task(self._read_loop())

            # 7. Start Blazor circuit for /deviceMessages
            self._circuit_started = time.monotonic()
            self._batches_dumped = 0
            self._toggle_handlers = {}
            self._toggles_attempted = {}
            self._pending_toggle_calls = {}
            self._renderer_interop_id = 1
            await self._send_start_circuit()
            await asyncio.sleep(0.3)
            await self._send_update_root_components()
            await asyncio.sleep(0.5)

            self.connected = True

            # Start keep-alive ping task
            self._ping_task = asyncio.create_task(self._ping_loop())

            _LOGGER.info("[Enpal WebSocket] Connected to /deviceMessages")
            return True

        except Exception as e:
            _LOGGER.error("[Enpal WebSocket] Connection failed: %s", e, exc_info=True)
            await self.close()
            return False

    def set_data_callback(
        self, callback: Optional[Callable[[Dict], Awaitable[None]]]
    ) -> None:
        """Register push-data callback (called on every RenderBatch)."""
        self._data_callback = callback

    async def fetch_data(self) -> Dict:
        """Fetch current sensor data by HTTP-scraping /deviceMessages.

        Returns the same format as :class:`EnpalHtmlClient`.
        If the scrape fails the connection is marked down so the
        coordinator will trigger a reconnect on the next cycle.
        """
        if not self.connected:
            raise RuntimeError("Not connected to Enpal Box")

        try:
            sensors = await self._scrape_and_parse()
        except Exception:
            self.connected = False
            raise
        # Refresh the baseline used for incremental RenderBatch patching.
        self._set_baseline(sensors)
        return {'sensors': sensors, 'source': 'websocket'}

    async def close(self) -> None:
        """Shut down WebSocket + HTTP session."""
        _LOGGER.debug("[Enpal WebSocket] Closing connection")
        await self._cleanup()
        _LOGGER.info("[Enpal WebSocket] Connection closed")

    async def _cleanup(self) -> None:
        """Release all resources (safe to call multiple times)."""
        self.connected = False

        for task in (self._ping_task, self._read_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._ping_task = None
        self._read_task = None

        if self.ws and not self.ws.closed:
            try:
                await self.ws.close()
            except Exception:
                pass
        self.ws = None

        if self.session and not self.session.closed:
            try:
                await self.session.close()
            except Exception:
                pass
        self.session = None

    def is_connected(self) -> bool:
        return self.connected

    # ------------------------------------------------------------------
    # HTTP scrape helper
    # ------------------------------------------------------------------

    async def _scrape_and_parse(self) -> List[Dict]:
        """HTTP GET /deviceMessages → parse with existing HTML parser."""
        from ..utils import parse_enpal_html_sensors

        url = f"{self.base_url}/deviceMessages"
        async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                raise ValueError(f"HTTP {resp.status} from {url}")
            html = await resp.text()

        sensors = parse_enpal_html_sensors(html, self.groups)
        _LOGGER.debug("[Enpal WebSocket] Scraped %d sensors from /deviceMessages", len(sensors))
        return sensors

    # ------------------------------------------------------------------
    # WebSocket message loop
    # ------------------------------------------------------------------

    async def _read_loop(self):
        """Background task - read and dispatch incoming WS messages."""
        try:
            self._last_activity = time.monotonic()
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    self._last_activity = time.monotonic()
                    await self._handle_messages(msg.data)
                elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING):
                    _LOGGER.warning("[Enpal WebSocket] Connection lost (type=%s), will reconnect on next poll", msg.type)
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            _LOGGER.error("[Enpal WebSocket] Read loop error: %s", e)
        finally:
            self.connected = False
            _LOGGER.info("[Enpal WebSocket] Read loop ended, connected=False")

    async def _ping_loop(self):
        """Send periodic SignalR keep-alive pings.

        Also detects stale connections: if no server message has been
        received for 3 × ping interval, the connection is considered dead.
        """
        stale_threshold = self._PING_INTERVAL * 3
        try:
            while self.connected and self.ws and not self.ws.closed:
                await asyncio.sleep(self._PING_INTERVAL)
                if not self.connected or not self.ws or self.ws.closed:
                    break
                # Check for stale connection (no server activity)
                silence = time.monotonic() - self._last_activity
                if silence > stale_threshold:
                    _LOGGER.warning(
                        "[Enpal WebSocket] No server activity for %.0fs, marking connection dead",
                        silence,
                    )
                    self.connected = False
                    break
                # Send keep-alive ping (SignalR type 6)
                ping_msg = encode_message([6])
                await self.ws.send_bytes(ping_msg)
                _LOGGER.debug("[Enpal WebSocket] Sent keep-alive ping")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            _LOGGER.debug("[Enpal WebSocket] Ping loop ended: %s", e)

    async def _handle_messages(self, data: bytes):
        """Dispatch decoded MessagePack messages."""
        messages = decode_messages(data)

        for msg in messages:
            if not isinstance(msg, list) or len(msg) == 0:
                continue

            msg_type = msg[0]

            # Type 6: Ping — server keep-alive; no response needed
            if msg_type == 6:
                continue

            # Type 3: Completion — response to our hub invocations
            if msg_type == 3:
                # [3, headers, invocationId, resultKind, result]
                result_kind = msg[3] if len(msg) > 3 else None
                inv_id = msg[2] if len(msg) > 2 else None
                result = msg[4] if len(msg) > 4 else None
                if result_kind == 1:
                    _LOGGER.error("[Enpal WebSocket] Server error for invocation %s: %s", inv_id, result)
                else:
                    _LOGGER.debug(
                        "[Enpal WebSocket] Completion for invocation %s: kind=%s result=%r",
                        inv_id, result_kind, result,
                    )
                continue

            # Type 7: Close — server is shutting down the connection
            if msg_type == 7:
                error = msg[1] if len(msg) > 1 else None
                _LOGGER.warning(
                    "[Enpal WebSocket] Server sent Close: %s (%.1fs after StartCircuit, "
                    "last targets seen: %s)",
                    error,
                    time.monotonic() - self._circuit_started,
                    ", ".join(self._recent_targets) or "none",
                )
                self.connected = False
                continue

            # Type 1: Invocation
            if msg_type != 1 or len(msg) < 4:
                _LOGGER.debug("[Enpal WebSocket] Unhandled message type %s: %r", msg_type, msg[:4])
                continue

            target = msg[3] if len(msg) > 3 else None
            args = msg[4] if len(msg) > 4 else []
            self._recent_targets.append(str(target))
            _LOGGER.debug(
                "[Enpal WebSocket] Invocation %s with %d arg(s)", target, len(args) if args else 0
            )

            if target == "JS.RenderBatch":
                # Acknowledge the render so the server keeps sending
                if args:
                    await self._send_on_render_completed(args[0])
                # Apply the incremental binary diff and push (debounced)
                batch_bytes = args[1] if len(args) > 1 else None
                await self._on_render_batch(batch_bytes)

            elif target == "JS.BeginInvokeJS":
                # Always acknowledge JS calls to keep circuit alive
                if len(args) >= 1:
                    identifier = args[1] if len(args) > 1 else ""
                    _LOGGER.debug(
                        "[Enpal WebSocket] JS call %s(%s)",
                        identifier,
                        str(args[2])[:200] if len(args) > 2 else "",
                    )
                    if len(args) > 2 and isinstance(args[2], str):
                        self._try_capture_renderer_interop_id(args[2])
                    await self._send_end_invoke_js(
                        args[0], _JS_CALL_RESULTS.get(identifier, "null")
                    )

            elif target == "JS.EndInvokeDotNet":
                # Response to our DispatchEventAsync calls (checkbox toggles)
                call_id = args[0] if args else None
                success = args[1] if len(args) > 1 else False
                try:
                    call_id_int = int(call_id)
                except (TypeError, ValueError):
                    call_id_int = None
                dom_id = self._pending_toggle_calls.pop(call_id_int, None)
                if dom_id is None:
                    continue
                if success:
                    _LOGGER.info(
                        "[Enpal WebSocket] Enabled page toggle '%s'", dom_id
                    )
                else:
                    # Keep the attempted handler id: a retry only happens
                    # once a later RenderBatch delivers a fresh handler id.
                    _LOGGER.warning(
                        "[Enpal WebSocket] Toggling '%s' failed: %s",
                        dom_id,
                        args[2] if len(args) > 2 else None,
                    )

            elif target == "JS.Error":
                _LOGGER.warning(
                    "[Enpal WebSocket] Circuit error reported by the box: %s",
                    args[0] if args else None,
                )

    async def _on_render_batch(self, batch_bytes=None):
        """React to a RenderBatch by patching the baseline from the binary diff.

        No HTTP scrape is performed here - the changed sensor rows are read
        directly from the RenderBatch payload.  The coordinator's periodic
        full scrape (which calls :meth:`fetch_data`) refreshes the baseline and
        corrects anything the fast path skips.
        """
        if self._data_callback is None:
            return

        strings: List[str] = []
        rows: List[Dict] = []
        if isinstance(batch_bytes, (bytes, bytearray)):
            try:
                strings = parse_render_batch_strings(bytes(batch_bytes))
                rows = extract_changed_rows(strings)
            except Exception:
                _LOGGER.exception("[Enpal WebSocket] RenderBatch decode failed")
            self._log_batch(len(batch_bytes), strings, rows)
            self._collect_toggle_handlers(bytes(batch_bytes))
            await self._activate_next_toggle()

        # Seed the baseline if we have not scraped yet (a push can arrive
        # before the coordinator's first poll completes).
        if self._baseline is None:
            try:
                sensors = await self._scrape_and_parse()
            except Exception:
                _LOGGER.exception("[Enpal WebSocket] Baseline scrape failed")
                return
            self._set_baseline(sensors)
            await self._push()
            return

        if rows:
            try:
                self._apply_diff(rows)
            except Exception:
                _LOGGER.exception("[Enpal WebSocket] Incremental diff failed")

        # Push to the coordinator (debounced).
        now = time.monotonic()
        if now - self._last_push_time < _PUSH_DEBOUNCE_SECONDS:
            return
        self._last_push_time = now
        await self._push()

    def _log_batch(self, size: int, strings: List[str], rows: List[Dict]) -> None:
        """Log RenderBatch metrics, plus the string table for the first big ones."""
        if not _LOGGER.isEnabledFor(logging.DEBUG):
            return
        _LOGGER.debug(
            "[Enpal WebSocket] RenderBatch: %d bytes, %d strings, %d sensor row(s), "
            "%d dotted key(s)",
            size, len(strings), len(rows),
            sum(1 for s in strings if "." in s and " " not in s and len(s) < 60),
        )
        if size < _BATCH_DUMP_MIN_BYTES or self._batches_dumped >= _BATCH_DUMP_LIMIT:
            return
        self._batches_dumped += 1
        dump = " | ".join(s.strip() for s in strings if s.strip())
        _LOGGER.debug(
            "[Enpal WebSocket] RenderBatch string table %d/%d: %s",
            self._batches_dumped, _BATCH_DUMP_LIMIT, dump[:_BATCH_DUMP_MAX_CHARS],
        )

    async def _push(self) -> None:
        """Send the current baseline to the registered data callback."""
        if self._data_callback is None or self._baseline is None:
            return
        try:
            await self._data_callback({'sensors': self._baseline, 'source': 'websocket'})
        except Exception:
            _LOGGER.exception("[Enpal WebSocket] Push callback failed")

    def _set_baseline(self, sensors: List[Dict]) -> None:
        """Store the full sensor list and (re)build the key → index map.

        The index maps ``make_id(<raw dotted key>)`` to the positions of the
        matching baseline sensors.  Keys that resolve to more than one sensor
        (the same dotted key under different groups) are considered ambiguous
        and skipped on the fast path.
        """
        from ..utils import make_id

        # Carry over sensors created from RenderBatch rows.  On firmware 8.51
        # the HTTP scrape does not contain the device rows, so a fresh scrape
        # would silently drop them on every periodic poll.
        if self._baseline:
            known = {make_id(s.get("name", "")) for s in sensors}
            for sensor in self._baseline:
                if sensor.get("raw_key") and make_id(sensor.get("name", "")) not in known:
                    sensors.append(sensor)

        self._baseline = sensors
        index: Dict[str, List[int]] = {}
        for i, sensor in enumerate(sensors):
            name = sensor.get("name", "")
            group = sensor.get("group", "")
            label = name
            prefix = f"{group}: "
            if group and name.startswith(prefix):
                label = name[len(prefix):]
            ids = {make_id(label)}
            if sensor.get("raw_key"):
                ids.add(make_id(sensor["raw_key"]))
            for key_id in ids:
                index.setdefault(key_id, []).append(i)
        self._key_index = index

    def _apply_diff(self, rows: List[Dict]) -> None:
        """Patch baseline sensors in place from extracted RenderBatch rows."""
        from ..utils import (
            make_id,
            get_class_and_unit,
            normalize_value_and_unit,
            is_strict_number,
        )
        from ..const import UNIT_DEVICE_CLASS_MAP, DEFAULT_UNITS, SENSOR_KEY_ALIASES

        patched = 0
        created = 0
        for row in rows:
            value = row.get("value")
            if not is_patchable_value(value):
                continue
            raw_key = row["key"]
            key = SENSOR_KEY_ALIASES.get(raw_key, raw_key)
            indices = self._key_index.get(make_id(raw_key)) or self._key_index.get(make_id(key))
            if not indices:
                # Unknown key: on firmware 8.51 the device rows never show up
                # in the HTTP scrape, so create the sensor from the row.
                if self._create_sensor_from_row(row):
                    created += 1
                continue
            # Ambiguous cross-group keys are left to the full scrape.
            if len(indices) != 1:
                continue

            sensor = self._baseline[indices[0]]
            unit_raw = row.get("unit")
            combined = value if not unit_raw else f"{value} {unit_raw}"
            unit, device_class = get_class_and_unit(combined, UNIT_DEVICE_CLASS_MAP)
            value_clean, unit = normalize_value_and_unit(
                combined, unit, device_class, DEFAULT_UNITS
            )

            # Guard against RenderBatch rows that only carried a timestamp
            # change: the unchanged value string is then absent from the diff,
            # so the row parser can pick up the timestamp as the value. Writing
            # such a non-numeric string into a numeric sensor (e.g. the lifetime
            # energy counter) makes Home Assistant drop the entity to
            # "unavailable". When the target sensor is numeric, only accept a
            # numeric value on the fast path and leave anything else to the
            # periodic full scrape.
            if self._is_numeric_sensor(sensor) and not is_strict_number(value_clean):
                continue

            sensor["value"] = value_clean
            if unit:
                sensor["unit"] = unit
            if row.get("timestamp"):
                sensor["enpal_last_update"] = row["timestamp"]
            patched += 1

        if patched:
            _LOGGER.debug("[Enpal WebSocket] Incrementally patched %d sensor(s)", patched)
        if created:
            _LOGGER.info("[Enpal WebSocket] Created %d sensor(s) from RenderBatch rows", created)

    def _create_sensor_from_row(self, row: Dict) -> bool:
        """Add a baseline sensor for a RenderBatch row with an unknown key.

        The row carries no group, so it is restored from the static
        ``SENSOR_KEY_GROUPS`` table.  Keys without a known group are skipped
        because a wrong group would produce a wrong entity id.
        """
        from ..utils import (
            make_id,
            friendly_name,
            get_class_and_unit,
            normalize_value_and_unit,
        )
        from ..const import (
            UNIT_DEVICE_CLASS_MAP,
            DEFAULT_UNITS,
            DEVICE_CLASS_OVERRIDES,
            SENSOR_KEY_ALIASES,
            SENSOR_KEY_GROUPS,
        )

        raw_key = row["key"]
        group = SENSOR_KEY_GROUPS.get(raw_key)
        if group is None or group not in self.groups:
            return False
        key = SENSOR_KEY_ALIASES.get(raw_key, raw_key)

        value = row.get("value")
        unit_raw = row.get("unit")
        combined = value if not unit_raw else f"{value} {unit_raw}"
        unit, device_class = get_class_and_unit(combined, UNIT_DEVICE_CLASS_MAP)
        value_clean, unit = normalize_value_and_unit(
            combined, unit, device_class, DEFAULT_UNITS
        )

        sensor = {
            "name": friendly_name(group, key),
            "value": value_clean,
            "unit": unit,
            "device_class": device_class,
            "enabled": True,
            "enpal_last_update": row.get("timestamp"),
            "group": group,
            "raw_key": raw_key,
        }
        sensor_id = make_id(sensor["name"])
        if sensor_id in DEVICE_CLASS_OVERRIDES:
            sensor["device_class"] = DEVICE_CLASS_OVERRIDES[sensor_id]

        idx = len(self._baseline)
        self._baseline.append(sensor)
        label = sensor["name"][len(f"{group}: "):]
        for key_id in {make_id(label), make_id(raw_key)}:
            self._key_index.setdefault(key_id, []).append(idx)
        _LOGGER.debug(
            "[Enpal WebSocket] Created sensor from RenderBatch: %s = %s %s",
            sensor["name"], value_clean, unit or "",
        )
        return True

    # ------------------------------------------------------------------
    # Page toggles (firmware 8.51: "Show unsupported/internal values")
    # ------------------------------------------------------------------

    def _collect_toggle_handlers(self, raw: bytes) -> None:
        """Remember event handler IDs of the show-hidden-values checkboxes.

        Handler IDs can change whenever the card re-renders, so the map is
        refreshed from every RenderBatch. Only toggles of selected sensor
        groups are collected.
        """
        for dom_id, handler_id in extract_event_handlers(raw).items():
            if not dom_id.startswith(_TOGGLE_ID_PREFIXES):
                continue
            group = dom_id.split("_", 1)[1]
            if group not in self.groups:
                continue
            if self._toggle_handlers.get(dom_id) != handler_id:
                _LOGGER.debug(
                    "[Enpal WebSocket] Toggle '%s' has handler id %d",
                    dom_id, handler_id,
                )
            self._toggle_handlers[dom_id] = handler_id

    async def _activate_next_toggle(self) -> None:
        """Click one pending checkbox so hidden sensor rows get rendered.

        One toggle per RenderBatch: each click triggers a re-render that may
        reassign the remaining handler IDs, and the next batch delivers the
        fresh ones. A toggle is retried only when a later batch shows a
        handler id different from the one already clicked.
        """
        # Not gated on self.connected: the initial page RenderBatch arrives
        # while connect() is still running.
        if self.ws is None or self.ws.closed:
            return
        for dom_id, handler_id in self._toggle_handlers.items():
            if self._toggles_attempted.get(dom_id) == handler_id:
                continue
            self._toggles_attempted[dom_id] = handler_id
            try:
                await self._send_checkbox_change(dom_id, handler_id)
            except Exception:
                _LOGGER.exception(
                    "[Enpal WebSocket] Sending toggle '%s' failed", dom_id
                )
            return

    async def _send_checkbox_change(self, dom_id: str, handler_id: int) -> None:
        """Dispatch a change event (checked=true) for a checkbox handler."""
        self._dotnet_call_counter += 1
        call_id = self._dotnet_call_counter
        self._pending_toggle_calls[call_id] = dom_id

        event_descriptor = {
            "eventHandlerId": handler_id,
            "eventName": "change",
            "eventFieldInfo": None,
        }
        event_args = {"type": "change", "value": True}
        args_json = json.dumps([event_descriptor, event_args])
        msg = [
            1, {}, None,  # fire-and-forget (response comes via JS.EndInvokeDotNet)
            "BeginInvokeDotNetFromJS",
            [str(call_id), None, "DispatchEventAsync", self._renderer_interop_id, args_json],
        ]
        await self._send_message(msg)
        _LOGGER.debug(
            "[Enpal WebSocket] Sent change event for '%s' (handler %d, call %d)",
            dom_id, handler_id, call_id,
        )

    def _try_capture_renderer_interop_id(self, args_json_str: str) -> None:
        """Extract the renderer's DotNet object reference from JS.BeginInvokeJS.

        Blazor calls attachWebRendererInterop with a DotNet object reference
        (serialized as {"__dotNetObject": N}); DispatchEventAsync must be
        invoked on that object.
        """
        if '"__dotNetObject"' not in args_json_str:
            return
        try:
            parsed = json.loads(args_json_str)
        except (json.JSONDecodeError, TypeError):
            return
        if not isinstance(parsed, list):
            return
        for item in parsed:
            if isinstance(item, dict) and isinstance(item.get("__dotNetObject"), int):
                obj_id = item["__dotNetObject"]
                if obj_id > 0:
                    self._renderer_interop_id = obj_id
                    _LOGGER.debug(
                        "[Enpal WebSocket] Captured renderer DotNet object ref: %d",
                        obj_id,
                    )
                    return

    @staticmethod
    def _is_numeric_sensor(sensor: Dict) -> bool:
        """Whether a baseline sensor is expected to hold a numeric state."""
        from ..utils import is_strict_number

        if sensor.get("device_class") in _NUMERIC_DEVICE_CLASSES:
            return True
        value = sensor.get("value")
        return isinstance(value, str) and is_strict_number(value)

    # ------------------------------------------------------------------
    # Blazor protocol messages
    # ------------------------------------------------------------------

    async def _send_start_circuit(self):
        """Initialise Blazor circuit pointing at /deviceMessages."""
        msg = [
            1, {}, "0", "StartCircuit",
            [
                self.base_url + "/",
                self.base_url + "/deviceMessages",
                "[]",
                self.application_state,
            ],
        ]
        await self._send_message(msg)

    async def _send_update_root_components(self):
        """Register pre-rendered Blazor components."""
        operations = [
            {
                "type": "add",
                "ssrComponentId": i + 1,
                "marker": {
                    "type": comp.type,
                    "prerenderId": comp.prerender_id,
                    "key": comp.key,
                    "sequence": comp.sequence,
                    "descriptor": comp.descriptor,
                    "uniqueId": i,
                },
            }
            for i, comp in enumerate(self.components)
        ]
        batch_json = json.dumps({"batchId": 1, "operations": operations})
        msg = [1, {}, None, "UpdateRootComponents", [batch_json, self.application_state]]
        await self._send_message(msg)

    async def _send_on_render_completed(self, batch_id: int):
        """Acknowledge a RenderBatch to keep the server sending."""
        msg = [1, {}, None, "OnRenderCompleted", [batch_id, None]]
        await self._send_message(msg)

    async def _send_end_invoke_js(self, task_id: int, result: str = "null"):
        """Acknowledge a JS invocation. ``result`` is raw JSON."""
        result_json = f"[{task_id},true,{result}]"
        msg = [1, {}, None, "EndInvokeJSFromDotNet", [task_id, True, result_json]]
        await self._send_message(msg)

    async def _send_message(self, msg: List):
        """Send a MessagePack message on the WebSocket."""
        data = encode_message(msg)
        await self.ws.send_bytes(data)
