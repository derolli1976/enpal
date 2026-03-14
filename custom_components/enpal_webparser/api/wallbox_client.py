"""Wallbox Blazor client for direct control via Enpal Box /wallbox page.

Connects to the /wallbox page via Blazor SignalR WebSocket, discovers
button event handler IDs from the RenderBatch, and enables:
- Reading wallbox status (mode + connection state) from RenderBatch data
- Clicking buttons (start/stop charging, set mode) via BeginInvokeDotNetFromJS
"""

import aiohttp
import asyncio
import json
import logging
import struct
import time
from typing import Optional, Dict, List

from .protocol import (
    ComponentDescriptor,
    extract_blazor_components,
    extract_application_state,
    encode_message,
    decode_messages,
)

_LOGGER = logging.getLogger(__name__)

# Wallbox button labels in DOM order (matches Enpal Box /wallbox page)
_BUTTON_ORDER = ["start", "stop", "eco", "full", "solar", "smart"]


class WallboxBlazorClient:
    """Client for the /wallbox Blazor page on the Enpal Box.

    Uses Blazor SignalR protocol to:
    - Read status (mode, connection state) from RenderBatch text content
    - Click buttons by dispatching browser events with discovered handler IDs
    """

    # Keep-alive ping interval (seconds) — Blazor Server expects periodic pings
    _PING_INTERVAL = 15
    # Max age (seconds) before reconnecting on next operation
    _MAX_CONNECTION_AGE = 300

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.components: List[ComponentDescriptor] = []
        self.application_state: str = ""
        self.connected: bool = False
        self._read_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._button_handlers: Dict[str, int] = {}  # e.g. {"start": 3, "eco": 5}
        self._mode: Optional[str] = None
        self._status: Optional[str] = None
        self._invocation_counter: int = 100
        self._status_event = asyncio.Event()
        self._click_event = asyncio.Event()  # Set when JS.EndInvokeDotNet arrives
        self._click_error: Optional[str] = None
        self._pending_click_call_id: Optional[int] = None
        self._dotnet_call_counter: int = 0
        self._renderer_interop_id: int = 1  # DotNet object ref ID (captured from JS.BeginInvokeJS)
        self._connected_at: float = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Connect to /wallbox and discover button event handler IDs."""
        await self._cleanup()

        try:
            _LOGGER.info("[Enpal Wallbox] Connecting to %s/wallbox", self.base_url)

            self.session = aiohttp.ClientSession(
                cookie_jar=aiohttp.CookieJar(),
                connector=aiohttp.TCPConnector(use_dns_cache=False),
            )

            # Load /wallbox HTML and extract Blazor bootstrap data
            async with self.session.get(f"{self.base_url}/wallbox") as resp:
                if resp.status != 200:
                    raise ValueError(f"HTTP {resp.status} loading /wallbox")
                html = await resp.text()
                self.components = extract_blazor_components(html)
                self.application_state = extract_application_state(html)

            if not self.components or not self.application_state:
                raise ValueError("No Blazor components or state found in /wallbox HTML")

            # Negotiate SignalR
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

            # Open WebSocket
            host = self.base_url.replace('http://', '').replace('https://', '')
            ws_url = f"ws://{host}/_blazor?id={connection_token}"
            self.ws = await self.session.ws_connect(ws_url)

            # Blazor handshake
            await self.ws.send_str('{"protocol":"blazorpack","version":1}\x1e')
            msg = await self.ws.receive()
            hs = msg.data if isinstance(msg.data, str) else msg.data.decode('utf-8')
            if '"error"' in hs.rstrip('\x1e'):
                raise ValueError(f"Handshake error: {hs}")

            # Start background reader
            self._read_task = asyncio.create_task(self._read_loop())

            # Initialize Blazor circuit for /wallbox
            await self._send_start_circuit()
            await asyncio.sleep(0.3)
            await self._send_update_root_components()

            # Wait for initial render batches (up to 5 seconds)
            for _ in range(50):
                await asyncio.sleep(0.1)
                if self._button_handlers and self._mode is not None:
                    break

            if not self._button_handlers:
                raise ValueError("No button handlers discovered from /wallbox")

            self.connected = True
            self._connected_at = time.monotonic()

            # Start keep-alive ping task
            self._ping_task = asyncio.create_task(self._ping_loop())

            _LOGGER.info(
                "[Enpal Wallbox] Connected. Mode=%s, Status=%s, Buttons=%s",
                self._mode, self._status, list(self._button_handlers.keys()),
            )
            return True

        except Exception as e:
            _LOGGER.error("[Enpal Wallbox] Connection failed: %s", e, exc_info=True)
            await self._cleanup()
            return False

    async def close(self) -> None:
        """Close connection."""
        _LOGGER.debug("[Enpal Wallbox] Closing connection")
        await self._cleanup()

    def is_connected(self) -> bool:
        return self.connected

    def get_mode(self) -> Optional[str]:
        """Return current wallbox mode (Eco, Full, Solar, Smart)."""
        return self._mode

    def get_status(self) -> Optional[str]:
        """Return current wallbox status (Connected, Charging, etc.)."""
        return self._status

    def _is_connection_stale(self) -> bool:
        """Check if the connection is too old and should be refreshed."""
        if not self.connected or not self.ws:
            return True
        if self.ws.closed:
            return True
        return (time.monotonic() - self._connected_at) > self._MAX_CONNECTION_AGE

    async def ensure_fresh_connection(self) -> bool:
        """Ensure connection is active and not stale. Reconnects if needed."""
        if self._is_connection_stale():
            _LOGGER.info("[Enpal Wallbox] Connection stale or closed, reconnecting")
            return await self.connect()
        return True

    async def click_button(self, button: str) -> bool:
        """Click a wallbox button by name.

        Ensures the connection is active before clicking.

        Args:
            button: One of 'start', 'stop', 'eco', 'full', 'solar', 'smart'

        Returns:
            True if the click was sent and acknowledged
        """
        _LOGGER.info("[Enpal Wallbox] Preparing to click '%s'", button)
        if not await self.ensure_fresh_connection():
            _LOGGER.error("[Enpal Wallbox] Failed to connect for click")
            return False

        handler_id = self._button_handlers.get(button)
        if handler_id is None:
            _LOGGER.error("[Enpal Wallbox] Unknown button: %s (available: %s)",
                          button, list(self._button_handlers.keys()))
            return False

        _LOGGER.info("[Enpal Wallbox] Clicking button '%s' (handler %d)", button, handler_id)

        # .NET 8 CircuitHub: dispatch events via BeginInvokeDotNetFromJS
        # calling DispatchEventAsync on the renderer's DotNet object reference
        self._dotnet_call_counter += 1
        call_id = self._dotnet_call_counter
        self._pending_click_call_id = call_id
        self._click_event.clear()
        self._click_error = None

        event_descriptor = {
            "eventHandlerId": handler_id,
            "eventName": "click",
            "eventFieldInfo": None,
        }
        event_args = {
            "type": "click",
            "detail": 1,
            "screenX": 0, "screenY": 0,
            "clientX": 0, "clientY": 0,
            "offsetX": 0, "offsetY": 0,
            "pageX": 0, "pageY": 0,
            "movementX": 0, "movementY": 0,
            "button": 0, "buttons": 0,
            "ctrlKey": False, "shiftKey": False,
            "altKey": False, "metaKey": False,
        }
        args_json = json.dumps([event_descriptor, event_args])
        click_msg = [
            1, {}, None,  # fire-and-forget (response comes via JS.EndInvokeDotNet)
            "BeginInvokeDotNetFromJS",
            [str(call_id), None, "DispatchEventAsync", self._renderer_interop_id, args_json],
        ]

        try:
            await self._send_message(click_msg)
            _LOGGER.debug("[Enpal Wallbox] Click message sent (call_id %d, renderer_id %d)",
                          call_id, self._renderer_interop_id)

            # Wait for JS.EndInvokeDotNet response from the server
            try:
                await asyncio.wait_for(self._click_event.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                _LOGGER.warning("[Enpal Wallbox] No JS.EndInvokeDotNet response for click '%s' (call_id %d)", button, call_id)
                return False

            if self._click_error:
                _LOGGER.error("[Enpal Wallbox] Server rejected click '%s': %s", button, self._click_error)
                return False

            # Click was accepted — wait briefly for RenderBatch with status update
            self._status_event.clear()
            try:
                await asyncio.wait_for(self._status_event.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                pass  # Mode may not have changed (e.g. clicking current mode)

            _LOGGER.info("[Enpal Wallbox] Button '%s' clicked successfully. Mode=%s, Status=%s",
                         button, self._mode, self._status)
            return True

        except Exception as e:
            _LOGGER.error("[Enpal Wallbox] Click failed: %s", e, exc_info=True)
            self.connected = False
            return False
        finally:
            self._pending_click_call_id = None

    async def start_charging(self) -> bool:
        return await self.click_button("start")

    async def stop_charging(self) -> bool:
        return await self.click_button("stop")

    async def set_mode(self, mode: str) -> bool:
        """Set wallbox mode. mode: 'eco', 'full', 'solar', 'smart'"""
        return await self.click_button(mode.lower())

    async def get_wallbox_data(self) -> Optional[Dict]:
        """Return current wallbox status as a dict (compatible with old addon API).

        Ensures the WebSocket connection is alive so that server-push
        RenderBatches keep the cached mode/status up to date.
        """
        if not await self.ensure_fresh_connection():
            return None
        return {
            "mode": self._mode.lower() if self._mode else None,
            "status": self._status.lower() if self._status else None,
            "success": True,
        }

    # ------------------------------------------------------------------
    # Internal: WebSocket message loop
    # ------------------------------------------------------------------

    async def _read_loop(self):
        """Background task to read and process incoming WS messages."""
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    await self._handle_messages(msg.data)
                elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING):
                    _LOGGER.warning("[Enpal Wallbox] Connection lost (type=%s)", msg.type)
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            _LOGGER.error("[Enpal Wallbox] Read loop error: %s", e)
        finally:
            self.connected = False

    async def _ping_loop(self):
        """Send periodic SignalR keep-alive pings."""
        try:
            while self.connected and self.ws and not self.ws.closed:
                await asyncio.sleep(self._PING_INTERVAL)
                if self.connected and self.ws and not self.ws.closed:
                    ping_msg = encode_message([6])
                    await self.ws.send_bytes(ping_msg)
                    _LOGGER.debug("[Enpal Wallbox] Sent keep-alive ping")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            _LOGGER.debug("[Enpal Wallbox] Ping loop ended: %s", e)

    async def _handle_messages(self, data: bytes):
        """Dispatch decoded MessagePack messages."""
        messages = decode_messages(data)

        for msg in messages:
            if not isinstance(msg, list) or len(msg) == 0:
                continue

            msg_type = msg[0]

            # Type 6: Ping — respond with pong (type 6)
            if msg_type == 6:
                continue

            # Type 3: Completion — response to a hub invocation (e.g. StartCircuit)
            if msg_type == 3:
                # [3, headers, invocationId, resultKind, result]
                # resultKind: 1=Error, 2=VoidResult, 3=NonVoidResult
                inv_id = msg[2] if len(msg) > 2 else None
                result_kind = msg[3] if len(msg) > 3 else None
                result = msg[4] if len(msg) > 4 else None

                if result_kind == 1:
                    _LOGGER.error("[Enpal Wallbox] Server error for invocation %s: %s", inv_id, result)
                elif result_kind == 3:
                    _LOGGER.debug("[Enpal Wallbox] Invocation %s result: %s",
                                  inv_id, repr(str(result)[:100]))
                else:
                    _LOGGER.debug("[Enpal Wallbox] Invocation %s completed (void)", inv_id)
                continue

            # Type 7: Close — server closing connection
            if msg_type == 7:
                error = msg[1] if len(msg) > 1 else None
                _LOGGER.warning("[Enpal Wallbox] Server sent Close message: %s", error)
                self.connected = False
                continue

            # Type 1: Invocation
            if msg_type != 1 or len(msg) < 4:
                _LOGGER.debug("[Enpal Wallbox] Unknown message type %s (len=%d)", msg_type, len(msg))
                continue

            target = msg[3] if len(msg) > 3 else None
            args = msg[4] if len(msg) > 4 else []

            if target == "JS.RenderBatch":
                batch_id = args[0] if args else None
                batch_data = args[1] if len(args) > 1 else None

                _LOGGER.debug("[Enpal Wallbox] RenderBatch id=%s, size=%d",
                              batch_id, len(batch_data) if isinstance(batch_data, bytes) else 0)

                if batch_data and isinstance(batch_data, bytes):
                    self._process_render_batch(batch_data)

                if batch_id is not None:
                    await self._send_on_render_completed(batch_id)

            elif target == "JS.BeginInvokeJS":
                task_id = args[0] if args else None
                identifier = args[1] if len(args) > 1 else None
                args_json_str = args[2] if len(args) > 2 else None
                _LOGGER.debug("[Enpal Wallbox] JS.BeginInvokeJS task=%s, id=%s",
                              task_id, identifier)

                # Capture DotNet object reference ID from attachWebRendererInterop
                if args_json_str and isinstance(args_json_str, str):
                    self._try_capture_renderer_interop_id(args_json_str)

                if task_id is not None:
                    await self._send_end_invoke_js(task_id)

            elif target == "JS.EndInvokeDotNet":
                # Response to our BeginInvokeDotNetFromJS calls
                # args = [callId, success, resultJsonOrError]
                call_id = args[0] if args else None
                success = args[1] if len(args) > 1 else False
                result = args[2] if len(args) > 2 else None

                # callId may arrive as int or string
                call_id_int = int(call_id) if call_id is not None else None

                if success:
                    _LOGGER.debug("[Enpal Wallbox] JS.EndInvokeDotNet call_id=%s succeeded", call_id)
                else:
                    _LOGGER.error("[Enpal Wallbox] JS.EndInvokeDotNet call_id=%s failed: %s", call_id, result)

                # Signal click completion if this matches our pending call
                if call_id_int is not None and call_id_int == self._pending_click_call_id:
                    self._click_error = result if not success else None
                    self._click_event.set()

            else:
                _LOGGER.debug("[Enpal Wallbox] Server invocation: %s", target)

    # ------------------------------------------------------------------
    # DotNet object reference capture
    # ------------------------------------------------------------------

    def _try_capture_renderer_interop_id(self, args_json_str: str):
        """Extract DotNet object reference ID from JS.BeginInvokeJS argsJson.

        In .NET 8 Blazor, the server calls attachWebRendererInterop with a
        DotNet object reference (serialized as {"__dotNetObject": N}).
        We need this ID for BeginInvokeDotNetFromJS → DispatchEventAsync.
        """
        if '"__dotNetObject"' not in args_json_str:
            return
        try:
            parsed = json.loads(args_json_str)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "__dotNetObject" in item:
                        obj_id = item["__dotNetObject"]
                        if isinstance(obj_id, int) and obj_id > 0:
                            self._renderer_interop_id = obj_id
                            _LOGGER.info(
                                "[Enpal Wallbox] Captured renderer DotNet object ref ID: %d",
                                obj_id,
                            )
                            return
        except (json.JSONDecodeError, TypeError):
            pass

    # ------------------------------------------------------------------
    # RenderBatch parsing
    # ------------------------------------------------------------------

    def _process_render_batch(self, data: bytes):
        """Extract button handler IDs and status text from RenderBatch data."""
        # 1. Find onclick event handler IDs
        handlers = self._find_onclick_handlers(data)
        if handlers:
            # Take last 6 handlers (skip navigation handlers)
            if len(handlers) >= 6:
                wallbox_handlers = handlers[-6:]
                self._button_handlers = dict(zip(_BUTTON_ORDER, wallbox_handlers))
                _LOGGER.debug("[Enpal Wallbox] Discovered button handlers: %s",
                              self._button_handlers)

        # 2. Extract mode and status text
        mode, status = self._extract_status_text(data)
        changed = False
        if mode and mode != self._mode:
            self._mode = mode
            changed = True
        if status and status != self._status:
            self._status = status
            changed = True
        if changed:
            self._status_event.set()
            _LOGGER.debug("[Enpal Wallbox] Status update: Mode=%s, Status=%s",
                          self._mode, self._status)

    @staticmethod
    def _find_onclick_handlers(data: bytes) -> List[int]:
        """Find event handler IDs from onclick attribute frames in RenderBatch."""
        if len(data) < 24:
            return []

        # Footer: last 20 bytes = 5 × Int32 section offsets
        footer = struct.unpack_from('<5I', data, len(data) - 20)
        ref_frames_offset = footer[1]
        disp_comp_offset = footer[2]

        if ref_frames_offset >= len(data) or disp_comp_offset >= len(data):
            return []

        pos = ref_frames_offset
        frame_count = struct.unpack_from('<I', data, pos)[0]
        pos += 4

        handlers = []
        frame_size = 20
        for _ in range(frame_count):
            if pos + frame_size > disp_comp_offset:
                break
            frame_type = struct.unpack_from('<I', data, pos)[0]
            if frame_type == 3:  # Attribute frame
                event_id = struct.unpack_from('<Q', data, pos + 12)[0]
                if event_id > 0:
                    handlers.append(event_id)
            pos += frame_size

        return handlers

    @staticmethod
    def _extract_status_text(data: bytes) -> tuple:
        """Extract 'Mode X' and 'Status Y' from RenderBatch binary data."""
        text = data.decode('utf-8', errors='replace')
        mode = None
        status = None

        valid_modes = {'Eco', 'Solar', 'Full', 'Smart', 'Fast'}

        idx = 0
        while True:
            idx = text.find('Mode ', idx)
            if idx < 0:
                break
            after = text[idx + 5:idx + 25]
            word = ''
            for c in after:
                if c.isalpha():
                    word += c
                elif word:
                    break
            if word in valid_modes:
                mode = word
                break
            idx += 5

        idx = 0
        while True:
            idx = text.find('Status ', idx)
            if idx < 0:
                break
            after = text[idx + 7:idx + 30]
            word = ''
            for c in after:
                if c.isalpha():
                    word += c
                elif word:
                    break
            if word and len(word) > 2:
                status = word
                break
            idx += 7

        return mode, status

    # ------------------------------------------------------------------
    # Blazor protocol messages
    # ------------------------------------------------------------------

    async def _send_start_circuit(self):
        msg = [
            1, {}, "0", "StartCircuit",
            [
                self.base_url + "/",
                self.base_url + "/wallbox",
                "[]",
                self.application_state,
            ],
        ]
        await self._send_message(msg)

    async def _send_update_root_components(self):
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
        msg = [1, {}, None, "OnRenderCompleted", [batch_id, None]]
        await self._send_message(msg)

    async def _send_end_invoke_js(self, task_id: int):
        result_json = f"[{task_id},true,null]"
        msg = [1, {}, None, "EndInvokeJSFromDotNet", [task_id, True, result_json]]
        await self._send_message(msg)

    async def _send_message(self, msg: List):
        data = encode_message(msg)
        await self.ws.send_bytes(data)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def _cleanup(self):
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
