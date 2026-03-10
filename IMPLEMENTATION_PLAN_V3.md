# Implementierungsplan: Version 3.0.0 - WebSocket API

## 🎯 Projektziele

1. **WebSocket-Client** für Enpal Box implementieren (basierend auf @arigon's Go-Library)
2. **Wallbox-Steuerung** direkt über WebSocket (Wallbox Add-on wird obsolet)
3. **Dual-Mode Support**: HTML-Parsing als Fallback
4. **Rückwärtskompatibilität**: Sanfte Migration für bestehende User

## 📋 Implementierungsphasen

### Phase 1: Grundlagen (Woche 1-2)

#### 1.1 Projektstruktur erweitern
```
custom_components/enpal_webparser/
├── api/
│   ├── __init__.py
│   ├── base.py              # Abstrakte EnpalApiClient Klasse
│   ├── html_client.py       # Bestehende HTML-Implementierung
│   └── websocket_client.py  # NEUE WebSocket-Implementierung
├── models.py                # Datenmodelle (CollectorData, etc.)
└── ...
```

#### 1.2 Dependencies hinzufügen
**manifest.json** erweitern:
```json
{
  "requirements": [
    "aiohttp>=3.9.0",
    "beautifulsoup4>=4.12.0",
    "msgpack>=1.0.7"  // NEU
  ]
}
```

#### 1.3 Basis-Klassen erstellen

**api/base.py**:
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class EnpalApiClient(ABC):
    """Abstrakte Basis-Klasse für Enpal API Clients"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Verbindung zur Enpal Box herstellen"""
        pass
    
    @abstractmethod
    async def fetch_data(self) -> Dict:
        """Daten von der Enpal Box abrufen"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Verbindung schließen"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Verbindungsstatus prüfen"""
        pass
```

**models.py**:
```python
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

@dataclass
class DataPoint:
    """Einzelner Datenpunkt"""
    value: Any
    unit: Optional[str] = None
    timestamp_utc: Optional[str] = None

@dataclass
class DeviceCollection:
    """Daten eines Geräts (Inverter, Battery, etc.)"""
    device_id: str
    device_class: str  # "Inverter", "Battery", "Wallbox", etc.
    timestamp_utc: str
    number_data_points: Dict[str, DataPoint]
    text_data_points: Dict[str, DataPoint]
    error_codes: List[Dict] = None

@dataclass
class CollectorData:
    """Gesamte Collector-Daten"""
    collection_id: str
    iot_device_id: str
    timestamp_utc: str
    device_collections: List[DeviceCollection]
    energy_management: List[Dict] = None
    error_codes: List[Dict] = None
```

### Phase 2: WebSocket-Client (Woche 3-4)

#### 2.1 Blazor-Komponenten-Extraktion

**api/websocket_client.py** - Teil 1:
```python
import re
import json
from typing import List, Dict, Optional

class ComponentDescriptor:
    """Blazor-Komponenten-Deskriptor"""
    def __init__(self):
        self.type: str = ""
        self.sequence: int = 0
        self.descriptor: str = ""
        self.prerender_id: str = ""
        self.key: Dict[str, str] = {}

def extract_blazor_components(html: str) -> List[ComponentDescriptor]:
    """Extrahiert Blazor-Komponenten aus HTML"""
    pattern = re.compile(r'<!--Blazor:(\{.+?\})-->')
    matches = pattern.findall(html)
    
    components = []
    for match in matches:
        # JSON decode
        json_str = match.replace(r'\u002B', '+').replace(r'\u002F', '/')
        try:
            comp_data = json.loads(json_str)
            if comp_data.get('type') == 'server':
                comp = ComponentDescriptor()
                comp.type = comp_data['type']
                comp.descriptor = comp_data.get('descriptor', '')
                comp.sequence = comp_data.get('sequence', 0)
                comp.prerender_id = comp_data.get('prerenderId', '')
                
                if 'key' in comp_data:
                    comp.key = {
                        'locationHash': comp_data['key'].get('locationHash', ''),
                        'formattedComponentKey': comp_data['key'].get('formattedComponentKey', '')
                    }
                components.append(comp)
        except json.JSONDecodeError:
            continue
    
    return components

def extract_application_state(html: str) -> str:
    """Extrahiert Application State aus HTML"""
    pattern = re.compile(r'<!--Blazor-Server-Component-State:([^-]+)-->')
    match = pattern.search(html)
    return match.group(1).strip() if match else ""
```

#### 2.2 MessagePack-Protokoll

**api/websocket_client.py** - Teil 2:
```python
import msgpack
import io
from typing import Any, List

def write_vlq(value: int) -> bytes:
    """Variable-Length Quantity encoding"""
    result = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if value > 0:
            b |= 0x80
        result.append(b)
        if value == 0:
            break
    return bytes(result)

def read_vlq(reader: io.BytesIO) -> int:
    """Variable-Length Quantity decoding"""
    result = 0
    shift = 0
    while True:
        b = reader.read(1)
        if not b:
            raise EOFError()
        byte = b[0]
        result |= (byte & 0x7F) << shift
        if byte & 0x80 == 0:
            break
        shift += 7
    return result

def encode_message(msg: List[Any]) -> bytes:
    """Kodiert Nachricht als MessagePack + VLQ"""
    payload = msgpack.packb(msg)
    result = bytearray()
    result.extend(write_vlq(len(payload)))
    result.extend(payload)
    return bytes(result)

def decode_messages(data: bytes) -> List[List[Any]]:
    """Dekodiert MessagePack-Nachrichten"""
    reader = io.BytesIO(data)
    messages = []
    
    while reader.tell() < len(data):
        try:
            length = read_vlq(reader)
            payload = reader.read(length)
            msg = msgpack.unpackb(payload, raw=False)
            messages.append(msg)
        except (EOFError, msgpack.exceptions.UnpackException):
            break
    
    return messages
```

#### 2.3 WebSocket-Client Hauptklasse

**api/websocket_client.py** - Teil 3:
```python
import aiohttp
import asyncio
import logging
from typing import Optional, Dict
from .base import EnpalApiClient
from ..models import CollectorData, DeviceCollection, DataPoint

_LOGGER = logging.getLogger(__name__)

class EnpalWebSocketClient(EnpalApiClient):
    """WebSocket-Client für Enpal Box"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.components: List[ComponentDescriptor] = []
        self.application_state: str = ""
        self.connected: bool = False
        self._result_queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        self._read_task: Optional[asyncio.Task] = None
    
    async def connect(self) -> bool:
        """Verbindung zur Enpal Box herstellen"""
        try:
            # 1. HTTP Session mit Cookie Jar
            self.session = aiohttp.ClientSession(
                cookie_jar=aiohttp.CookieJar()
            )
            
            # 2. Collector-Seite laden
            async with self.session.get(f"{self.base_url}/collector") as resp:
                html = await resp.text()
                self.components = extract_blazor_components(html)
                self.application_state = extract_application_state(html)
            
            if not self.components or not self.application_state:
                raise ValueError("Keine Blazor-Komponenten gefunden")
            
            # 3. WebSocket Negotiate
            async with self.session.post(
                f"{self.base_url}/_blazor/negotiate?negotiateVersion=1",
                data=""
            ) as resp:
                negotiate_data = await resp.json()
                connection_token = negotiate_data['connectionToken']
            
            # 4. WebSocket verbinden
            host = self.base_url.replace('http://', '')
            ws_url = f"ws://{host}/_blazor?id={connection_token}"
            
            self.ws = await self.session.ws_connect(ws_url)
            
            # 5. Blazor Handshake
            await self.ws.send_str('{"protocol":"blazorpack","version":1}\x1e')
            msg = await self.ws.receive()
            # Handshake-Response prüfen
            
            # 6. Read Loop starten
            self._read_task = asyncio.create_task(self._read_loop())
            
            # 7. Blazor Circuit initialisieren
            await self._send_start_circuit()
            await asyncio.sleep(0.3)
            
            await self._send_update_root_components()
            await asyncio.sleep(0.5)
            
            self.connected = True
            _LOGGER.info("[Enpal WebSocket] Verbindung hergestellt")
            return True
            
        except Exception as e:
            _LOGGER.error(f"[Enpal WebSocket] Verbindung fehlgeschlagen: {e}")
            await self.close()
            return False
    
    async def fetch_data(self) -> Dict:
        """Daten abrufen (Button-Click simulieren)"""
        if not self.connected:
            raise RuntimeError("Nicht verbunden")
        
        # Queue leeren
        while not self._result_queue.empty():
            self._result_queue.get_nowait()
        
        # Button-Click senden (EventHandler ID 4)
        await self._click_button(4)
        
        # Auf Antwort warten (max 15 Sekunden)
        try:
            result_json = await asyncio.wait_for(
                self._result_queue.get(),
                timeout=15.0
            )
            return json.loads(result_json)
        except asyncio.TimeoutError:
            raise TimeoutError("Timeout beim Abrufen der Daten")
    
    async def close(self) -> None:
        """Verbindung schließen"""
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
        
        _LOGGER.info("[Enpal WebSocket] Verbindung geschlossen")
    
    def is_connected(self) -> bool:
        return self.connected
    
    # Private Methoden
    
    async def _read_loop(self):
        """Message Read Loop"""
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    await self._handle_messages(msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break
        except asyncio.CancelledError:
            pass
    
    async def _handle_messages(self, data: bytes):
        """MessagePack-Nachrichten verarbeiten"""
        messages = decode_messages(data)
        
        for msg in messages:
            if len(msg) < 4:
                continue
            
            msg_type = msg[0]
            if msg_type != 1:
                continue
            
            target = msg[3] if len(msg) > 3 else None
            args = msg[4] if len(msg) > 4 else []
            
            if target == "JS.RenderBatch":
                if args:
                    await self._send_on_render_completed(args[0])
            
            elif target == "JS.BeginInvokeJS":
                if len(args) >= 3:
                    task_id = args[0]
                    identifier = args[1]
                    
                    if identifier == "blazorMonaco.editor.setValue":
                        data_str = args[2]
                        json_data = self._extract_json(data_str)
                        if json_data:
                            await self._result_queue.put(json_data)
                    
                    await self._send_end_invoke_js(task_id)
    
    async def _send_start_circuit(self):
        """StartCircuit-Nachricht senden"""
        msg = [
            1, {}, "0", "StartCircuit",
            [self.base_url + "/", self.base_url + "/collector", 
             "[]", self.application_state]
        ]
        await self._send_message(msg)
    
    async def _send_update_root_components(self):
        """UpdateRootComponents-Nachricht senden"""
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
            1, {}, None, "UpdateRootComponents",
            [batch_json, self.application_state]
        ]
        await self._send_message(msg)
    
    async def _click_button(self, event_handler_id: int):
        """Button-Click simulieren"""
        event_info = {
            "eventHandlerId": event_handler_id,
            "eventName": "click",
            "eventFieldInfo": None
        }
        event_args = {
            "detail": 1, "button": 0, "buttons": 0,
            "ctrlKey": False, "shiftKey": False,
            "altKey": False, "metaKey": False,
            "type": "click"
        }
        event_json = json.dumps([event_info, event_args])
        
        msg = [
            1, {}, None, "BeginInvokeDotNetFromJS",
            ["1", None, "DispatchEventAsync", 1, event_json]
        ]
        await self._send_message(msg)
    
    async def _send_on_render_completed(self, batch_id: int):
        """OnRenderCompleted senden"""
        msg = [1, {}, None, "OnRenderCompleted", [batch_id, None]]
        await self._send_message(msg)
    
    async def _send_end_invoke_js(self, task_id: int):
        """EndInvokeJSFromDotNet senden"""
        result_json = f"[{task_id},true,null]"
        msg = [1, {}, None, "EndInvokeJSFromDotNet", 
               [task_id, True, result_json]]
        await self._send_message(msg)
    
    async def _send_message(self, msg: List):
        """MessagePack-Nachricht senden"""
        data = encode_message(msg)
        await self.ws.send_bytes(data)
    
    def _extract_json(self, raw_data: str) -> Optional[str]:
        """JSON aus rohem String extrahieren"""
        try:
            data_array = json.loads(raw_data)
            if isinstance(data_array, list) and len(data_array) >= 2:
                return data_array[1]
        except json.JSONDecodeError:
            pass
        return None
```

### Phase 3: Integration (Woche 5)

#### 3.1 Config Flow erweitern

**config_flow.py** - Neue Option:
```python
async def async_step_connection_type(self, user_input=None):
    """Verbindungstyp wählen"""
    if user_input is not None:
        self.connection_type = user_input["connection_type"]
        return await self.async_step_url()
    
    return self.async_show_form(
        step_id="connection_type",
        data_schema=vol.Schema({
            vol.Required("connection_type", default="websocket"): vol.In({
                "websocket": "WebSocket API (empfohlen)",
                "html": "HTML Parsing (Fallback)"
            })
        })
    )
```

#### 3.2 Sensor Platform anpassen

**sensor.py** - Client Factory:
```python
def create_api_client(config_entry) -> EnpalApiClient:
    """API Client erstellen"""
    connection_type = config_entry.data.get("connection_type", "websocket")
    base_url = config_entry.data["url"]
    
    if connection_type == "websocket":
        return EnpalWebSocketClient(base_url)
    else:
        return HtmlParserClient(base_url)
```

### Phase 4: Wallbox-Steuerung (Woche 6)

**@arigon's Hinweis**: Wallbox-Steuerung geht über die gleiche WebSocket-Session!

#### 4.1 Wallbox-Kommandos in WebSocket-Client

```python
# In EnpalWebSocketClient:

async def set_wallbox_mode(self, mode: str) -> bool:
    """Wallbox-Modus setzen (eco/solar/full)"""
    # Event-Handler ID muss ermittelt werden (Reverse Engineering)
    # Ähnlich wie Button-Click, aber mit anderen Parametern
    pass

async def start_wallbox_charging(self) -> bool:
    """Wallbox-Laden starten"""
    pass

async def stop_wallbox_charging(self) -> bool:
    """Wallbox-Laden stoppen"""
    pass
```

#### 4.2 Wallbox-Entities ohne Add-on

**button.py, switch.py, select.py** - Direkt über WebSocket:
```python
class EnpalWallboxButton(CoordinatorEntity, ButtonEntity):
    async def async_press(self) -> None:
        """Button gedrückt"""
        client = self.coordinator.client
        if isinstance(client, EnpalWebSocketClient):
            await client.start_wallbox_charging()
        else:
            # Fallback auf Add-on
            pass
```

### Phase 5: Testing & Dokumentation (Woche 7-8)

#### 5.1 Unit Tests
```python
# tests/test_websocket_client.py
# tests/test_message_encoding.py
# tests/test_component_extraction.py
```

#### 5.2 Integration Tests
- Echte Enpal Box
- Verschiedene Hardware-Varianten
- Wallbox-Steuerung

#### 5.3 Dokumentation
- README.md updaten
- MIGRATION_V3.md erstellen
- Release Notes 3.0.0

## 📅 Zeitplan

| Woche | Phase | Aufgaben |
|-------|-------|----------|
| 1-2 | Grundlagen | Projektstruktur, Base Classes, Models |
| 3-4 | WebSocket | Client-Implementierung, MessagePack |
| 5 | Integration | Config Flow, Sensor Platform |
| 6 | Wallbox | Steuerung über WebSocket |
| 7-8 | Testing | Tests, Dokumentation, Beta |

**Geschätzte Gesamtdauer**: 8 Wochen

## 🎯 Meilensteine

- **M1** (Woche 2): Projektstruktur steht
- **M2** (Woche 4): WebSocket-Client funktioniert
- **M3** (Woche 5): Daten in Home Assistant
- **M4** (Woche 6): Wallbox-Steuerung funktioniert
- **M5** (Woche 8): Beta-Release v3.0.0-beta1

## 🔍 Nächste Schritte (sofort)

1. **Branch erstellen**: `feature/v3.0-websocket`
2. **Milestone bestätigen**: v3.0.0 in GitHub
3. **Issue #11 updaten**: Implementierungsplan teilen
4. **Dependencies testen**: msgpack in HA-Umgebung
5. **Proof of Concept**: Minimaler WebSocket-Client

## 🤝 Zusammenarbeit

- **@arigon kontaktieren**: Fragen zum Protokoll
- **@Trustmania einbinden**: Original Feature Request
- **Community informieren**: GitHub Discussions
- **Beta-Tester suchen**: Verschiedene Hardware

## ⚠️ Kritische Punkte

1. **Cookie-Handling**: Muss perfekt sein (Session-Problem)
2. **Wallbox Event IDs**: Müssen durch Reverse Engineering gefunden werden
3. **MessagePack-Details**: Edge Cases beachten
4. **Blazor-Updates**: Enpal könnte Framework updaten

## 🎉 Erwartete Vorteile v3.0

- ✅ **Echtzeit-Updates** statt Polling
- ✅ **Strukturierte Daten** (JSON statt HTML)
- ✅ **Wallbox ohne Add-on**
- ✅ **Geringere Last** auf Enpal Box
- ✅ **Mehr Datenpunkte**
- ✅ **Zukunftssicherheit**

---

**Status**: Ready to Start 🚀  
**Nächster Schritt**: Branch erstellen und Projektstruktur aufbauen
