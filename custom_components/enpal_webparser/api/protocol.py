"""Blazor SignalR protocol helpers"""
import re
import json
import msgpack
import io
import logging
from typing import List, Any, Optional

_LOGGER = logging.getLogger(__name__)


# Inline ComponentDescriptor to avoid circular imports in standalone mode
class ComponentDescriptor:
    """Blazor server component descriptor"""
    def __init__(self):
        self.type: str = ""
        self.sequence: int = 0
        self.descriptor: str = ""
        self.prerender_id: str = ""
        self.key: dict = {}


def extract_blazor_components(html: str) -> List[ComponentDescriptor]:
    """
    Extract Blazor server components from HTML.
    
    Args:
        html: HTML page content
        
    Returns:
        List of ComponentDescriptor objects
    """
    pattern = re.compile(r'<!--Blazor:(\{.+?\})-->')
    matches = pattern.findall(html)
    
    components = []
    for match in matches:
        try:
            # Decode escaped characters
            json_str = match.replace(r'\u002B', '+').replace(r'\u002F', '/')
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
        except json.JSONDecodeError as e:
            _LOGGER.debug(f"[Enpal WebSocket] Failed to parse component: {e}")
            continue
    
    return components


def extract_application_state(html: str) -> str:
    """
    Extract Blazor application state from HTML.
    
    Args:
        html: HTML page content
        
    Returns:
        Application state string, or empty string if not found
    """
    pattern = re.compile(r'<!--Blazor-Server-Component-State:([^-]+)-->')
    match = pattern.search(html)
    return match.group(1).strip() if match else ""


def write_vlq(value: int) -> bytes:
    """
    Encode integer as Variable-Length Quantity.
    
    Args:
        value: Integer to encode
        
    Returns:
        VLQ-encoded bytes
    """
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
    """
    Decode Variable-Length Quantity from byte stream.
    
    Args:
        reader: BytesIO reader
        
    Returns:
        Decoded integer
        
    Raises:
        EOFError: If reader is exhausted
    """
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
    """
    Encode message as MessagePack with VLQ length prefix.
    
    Args:
        msg: Message as list
        
    Returns:
        VLQ-prefixed MessagePack bytes
    """
    payload = msgpack.packb(msg)
    result = bytearray()
    result.extend(write_vlq(len(payload)))
    result.extend(payload)
    return bytes(result)


def decode_messages(data: bytes) -> List[List[Any]]:
    """
    Decode multiple MessagePack messages from byte stream.
    
    Args:
        data: Raw bytes containing one or more messages
        
    Returns:
        List of decoded messages (each message is a list)
    """
    reader = io.BytesIO(data)
    messages = []
    
    while reader.tell() < len(data):
        try:
            length = read_vlq(reader)
            payload = reader.read(length)
            msg = msgpack.unpackb(payload, raw=False)
            messages.append(msg)
        except (EOFError, msgpack.exceptions.UnpackException) as e:
            _LOGGER.debug(f"[Enpal WebSocket] Message decode error: {e}")
            break
    
    return messages


def extract_json_from_blazor_data(raw_data: str) -> Optional[str]:
    """
    Extract JSON data from Blazor setValue call.
    
    Args:
        raw_data: Raw data string from blazorMonaco.editor.setValue
        
    Returns:
        JSON string if found, None otherwise
    """
    try:
        data_array = json.loads(raw_data)
        if isinstance(data_array, list) and len(data_array) >= 2:
            return data_array[1]
    except json.JSONDecodeError:
        pass
    return None
