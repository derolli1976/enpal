"""WebSocket client for Enpal Box using Blazor SignalR protocol"""
import aiohttp
import asyncio
import json
import logging
from typing import Optional, Dict, List
from .base import EnpalApiClient
from .protocol import (
    ComponentDescriptor,
    extract_blazor_components,
    extract_application_state,
    encode_message,
    decode_messages,
    extract_json_from_blazor_data,
)

_LOGGER = logging.getLogger(__name__)


class EnpalWebSocketClient(EnpalApiClient):
    """WebSocket client for Enpal Box using Blazor SignalR protocol"""

    def __init__(self, base_url: str, groups: List[str] = None):
        """
        Initialize WebSocket client.
        
        Args:
            base_url: Base URL of Enpal Box (e.g., http://192.168.1.100)
            groups: List of sensor groups to parse (default: all groups)
        """
        self.base_url = base_url.rstrip('/')
        self.groups = groups or [
            'Battery', 'Inverter', 'IoTEdgeDevice', 
            'PowerSensor', 'Wallbox', 'Site Data', 'Heatpump'
        ]
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.components: List[ComponentDescriptor] = []
        self.application_state: str = ""
        self.connected: bool = False
        self._result_queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        self._read_task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        """
        Establish WebSocket connection to Enpal Box.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            _LOGGER.info("[Enpal WebSocket] Connecting to %s", self.base_url)
            
            # 1. Create HTTP session with cookie jar (critical for session management!)
            # Use trust_env=False to avoid aiodns issues on Windows
            self.session = aiohttp.ClientSession(
                cookie_jar=aiohttp.CookieJar(),
                connector=aiohttp.TCPConnector(use_dns_cache=False)
            )
            
            # 2. Load collector page and extract Blazor components
            _LOGGER.debug("[Enpal WebSocket] Loading /collector page")
            async with self.session.get(f"{self.base_url}/collector") as resp:
                if resp.status != 200:
                    raise ValueError(f"HTTP {resp.status} when loading /collector")
                html = await resp.text()
                self.components = extract_blazor_components(html)
                self.application_state = extract_application_state(html)
            
            if not self.components:
                raise ValueError("No Blazor components found in HTML")
            if not self.application_state:
                raise ValueError("No application state found in HTML")
            
            _LOGGER.debug("[Enpal WebSocket] Found %d components", len(self.components))
            
            # 3. Negotiate WebSocket connection
            _LOGGER.debug("[Enpal WebSocket] Negotiating WebSocket connection")
            async with self.session.post(
                f"{self.base_url}/_blazor/negotiate?negotiateVersion=1",
                data=""
            ) as resp:
                if resp.status != 200:
                    raise ValueError(f"HTTP {resp.status} during negotiate")
                negotiate_data = await resp.json()
                connection_token = negotiate_data.get('connectionToken')
                if not connection_token:
                    raise ValueError("No connectionToken in negotiate response")
            
            # 4. Connect WebSocket
            host = self.base_url.replace('http://', '').replace('https://', '')
            ws_url = f"ws://{host}/_blazor?id={connection_token}"
            
            _LOGGER.debug("[Enpal WebSocket] Connecting to %s", ws_url)
            self.ws = await self.session.ws_connect(ws_url)
            
            # 5. Blazor handshake
            _LOGGER.debug("[Enpal WebSocket] Performing Blazor handshake")
            await self.ws.send_str('{"protocol":"blazorpack","version":1}\x1e')
            
            # Read handshake response (can be TEXT or BINARY)
            msg = await self.ws.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                handshake_response = msg.data.rstrip('\x1e')
            elif msg.type == aiohttp.WSMsgType.BINARY:
                handshake_response = msg.data.decode('utf-8').rstrip('\x1e')
            else:
                raise ValueError(f"Unexpected handshake response type: {msg.type}")
            
            _LOGGER.debug("[Enpal WebSocket] Handshake response: %s", handshake_response)
            
            # Check for error in handshake
            if '"error"' in handshake_response:
                raise ValueError(f"Handshake error: {handshake_response}")
            
            # 6. Start message read loop
            self._read_task = asyncio.create_task(self._read_loop())
            
            # 7. Initialize Blazor circuit
            _LOGGER.debug("[Enpal WebSocket] Starting Blazor circuit")
            await self._send_start_circuit()
            await asyncio.sleep(0.3)
            
            _LOGGER.debug("[Enpal WebSocket] Updating root components")
            await self._send_update_root_components()
            await asyncio.sleep(0.5)
            
            self.connected = True
            _LOGGER.info("[Enpal WebSocket] Connection established successfully")
            return True
            
        except Exception as e:
            _LOGGER.error("[Enpal WebSocket] Connection failed: %s", e, exc_info=True)
            await self.close()
            return False

    async def fetch_data(self) -> Dict:
        """
        Fetch data from Enpal Box by simulating button click.
        
        Returns:
            Dictionary with structure:
            {
                'sensors': List[Dict[str, Any]],
                'source': 'websocket',
            }
            
        Raises:
            RuntimeError: If not connected
            TimeoutError: If data fetch times out
        """
        if not self.connected:
            raise RuntimeError("Not connected to Enpal Box")
        
        _LOGGER.debug("[Enpal WebSocket] Fetching data")
        
        # Clear result queue
        while not self._result_queue.empty():
            self._result_queue.get_nowait()
        
        # Simulate button click (EventHandler ID 4 = "Load Current Collector State")
        await self._click_button(4)
        
        # Wait for response (max 15 seconds)
        try:
            result_json = await asyncio.wait_for(
                self._result_queue.get(),
                timeout=15.0
            )
            _LOGGER.debug("[Enpal WebSocket] Data received")
            json_data = json.loads(result_json)
            
            # Parse JSON to sensor format
            from .websocket_parser import parse_websocket_json_to_sensors
            
            # Get groups from stored config (need to pass this in constructor)
            groups = getattr(self, 'groups', [
                'Battery', 'Inverter', 'IoTEdgeDevice', 
                'PowerSensor', 'Wallbox', 'Site Data'
            ])
            
            sensors = parse_websocket_json_to_sensors(json_data, groups)
            
            return {
                'sensors': sensors,
                'source': 'websocket',
                'raw_data': json_data,  # Keep raw data for debugging
            }
            
        except asyncio.TimeoutError:
            _LOGGER.error("[Enpal WebSocket] Timeout waiting for data")
            raise TimeoutError("Timeout while fetching data from Enpal Box")

    async def close(self) -> None:
        """Close WebSocket connection"""
        _LOGGER.debug("[Enpal WebSocket] Closing connection")
        self.connected = False
        
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        if self.ws:
            await self.ws.close()
        
        if self.session:
            await self.session.close()
        
        _LOGGER.info("[Enpal WebSocket] Connection closed")

    def is_connected(self) -> bool:
        """Check if connected to Enpal Box"""
        return self.connected

    # Private methods

    async def _read_loop(self):
        """Message read loop - runs in background task"""
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    await self._handle_messages(msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.error("[Enpal WebSocket] WebSocket error")
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            _LOGGER.error("[Enpal WebSocket] Read loop error: %s", e)

    async def _handle_messages(self, data: bytes):
        """Handle incoming MessagePack messages"""
        messages = decode_messages(data)
        
        for msg in messages:
            if len(msg) < 4:
                continue
            
            msg_type = msg[0]
            if msg_type != 1:  # Only handle StreamInvocation (type 1)
                continue
            
            target = msg[3] if len(msg) > 3 else None
            args = msg[4] if len(msg) > 4 else []
            
            if target == "JS.RenderBatch":
                # Server finished rendering - acknowledge
                if args:
                    batch_id = args[0]
                    await self._send_on_render_completed(batch_id)
            
            elif target == "JS.BeginInvokeJS":
                # Server wants to call JavaScript function
                if len(args) >= 3:
                    task_id = args[0]
                    identifier = args[1]
                    
                    # Check if this is the editor.setValue call with our data
                    if identifier == "blazorMonaco.editor.setValue":
                        data_str = args[2]
                        json_data = extract_json_from_blazor_data(data_str)
                        if json_data:
                            _LOGGER.debug("[Enpal WebSocket] Received collector data")
                            await self._result_queue.put(json_data)
                    
                    # Always acknowledge JS invocation
                    await self._send_end_invoke_js(task_id)

    async def _send_start_circuit(self):
        """Send StartCircuit message to initialize Blazor circuit"""
        msg = [
            1,  # StreamInvocation
            {},  # Headers
            "0",  # InvocationId
            "StartCircuit",  # Target
            [
                self.base_url + "/",  # Base URL
                self.base_url + "/collector",  # Location
                "[]",  # Unknown parameter
                self.application_state  # Application state
            ]
        ]
        await self._send_message(msg)

    async def _send_update_root_components(self):
        """Send UpdateRootComponents message to register UI components"""
        operations = []
        for i, comp in enumerate(self.components):
            operations.append({
                "type": "add",
                "ssrComponentId": i + 1,
                "marker": {
                    "type": comp.type,
                    "prerenderId": comp.prerender_id,
                    "key": comp.key,
                    "sequence": comp.sequence,
                    "descriptor": comp.descriptor,
                    "uniqueId": i
                }
            })
        
        batch = {"batchId": 1, "operations": operations}
        batch_json = json.dumps(batch)
        
        msg = [
            1,  # StreamInvocation
            {},  # Headers
            None,  # InvocationId
            "UpdateRootComponents",  # Target
            [batch_json, self.application_state]
        ]
        await self._send_message(msg)

    async def _click_button(self, event_handler_id: int):
        """
        Simulate button click.
        
        Args:
            event_handler_id: Event handler ID (4 = "Load Current Collector State")
        """
        event_info = {
            "eventHandlerId": event_handler_id,
            "eventName": "click",
            "eventFieldInfo": None
        }
        event_args = {
            "detail": 1,
            "button": 0,
            "buttons": 0,
            "ctrlKey": False,
            "shiftKey": False,
            "altKey": False,
            "metaKey": False,
            "type": "click"
        }
        event_json = json.dumps([event_info, event_args])
        
        msg = [
            1,  # StreamInvocation
            {},  # Headers
            None,  # InvocationId
            "BeginInvokeDotNetFromJS",  # Target
            ["1", None, "DispatchEventAsync", 1, event_json]
        ]
        await self._send_message(msg)

    async def _send_on_render_completed(self, batch_id: int):
        """Acknowledge render completion"""
        msg = [
            1,  # StreamInvocation
            {},  # Headers
            None,  # InvocationId
            "OnRenderCompleted",  # Target
            [batch_id, None]
        ]
        await self._send_message(msg)

    async def _send_end_invoke_js(self, task_id: int):
        """Acknowledge JavaScript invocation completion"""
        result_json = f"[{task_id},true,null]"
        msg = [
            1,  # StreamInvocation
            {},  # Headers
            None,  # InvocationId
            "EndInvokeJSFromDotNet",  # Target
            [task_id, True, result_json]
        ]
        await self._send_message(msg)

    async def _send_message(self, msg: List):
        """
        Send MessagePack message to server.
        
        Args:
            msg: Message as list
        """
        data = encode_message(msg)
        await self.ws.send_bytes(data)
