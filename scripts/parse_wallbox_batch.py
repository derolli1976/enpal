"""Parse Blazor RenderBatch binary format to extract event handler IDs and text content."""
import asyncio
import aiohttp
import json
import msgpack
import io
import re
import struct


def write_vlq(value):
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


def read_vlq(reader):
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


def decode_messages(data):
    reader = io.BytesIO(data)
    messages = []
    while reader.tell() < len(data):
        try:
            length = read_vlq(reader)
            payload = reader.read(length)
            msg = msgpack.unpackb(payload, raw=False)
            messages.append(msg)
        except:
            break
    return messages


def encode_message(msg):
    payload = msgpack.packb(msg)
    result = bytearray()
    result.extend(write_vlq(len(payload)))
    result.extend(payload)
    return bytes(result)


def extract_components(html):
    pattern = re.compile(r'<!--Blazor:(\{.+?\})-->')
    matches = pattern.findall(html)
    comps = []
    for match in matches:
        json_str = match.replace(r'\u002B', '+').replace(r'\u002F', '/')
        try:
            cd = json.loads(json_str)
            if cd.get('type') == 'server':
                comps.append(cd)
        except:
            pass
    return comps


def extract_app_state(html):
    m = re.search(r'<!--Blazor-Server-Component-State:([^-]+)-->', html)
    return m.group(1).strip() if m else ''


def read_dotnet_string(data, offset):
    """Read a .NET BinaryWriter string (7-bit encoded length + UTF-8)."""
    pos = offset
    length = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        length |= (b & 0x7F) << shift
        if b & 0x80 == 0:
            break
        shift += 7
    if pos + length > len(data):
        return None, offset
    text = data[pos:pos + length].decode('utf-8', errors='replace')
    return text, pos + length


def parse_render_batch(data):
    """Parse the Blazor RenderBatch binary format.
    
    Format (from ASP.NET Core WebRenderBatchWriter.cs):
    - Section 1: Updated Components
    - Section 2: Reference Frames (20 bytes each)
    - Section 3: Disposed Component IDs
    - Section 4: Disposed Event Handler IDs
    - Section 5: String Table
    - Footer: 5 x Int32 section offsets
    """
    if len(data) < 20:
        print(f"  Batch too small ({len(data)} bytes)")
        return
    
    # Try reading footer (last 20 bytes = 5 Int32 offsets)
    footer_offset = len(data) - 20
    offsets = struct.unpack_from('<5I', data, footer_offset)
    print(f"  Footer offsets: updatedComponents={offsets[0]}, referenceFrames={offsets[1]}, "
          f"disposedComponents={offsets[2]}, disposedEventHandlers={offsets[3]}, strings={offsets[4]}")
    
    # Check if offsets are reasonable
    all_valid = all(o < len(data) for o in offsets)
    if not all_valid:
        print(f"  WARNING: Some offsets exceed data length ({len(data)})")
        # Try different footer sizes
        for footer_size in [16, 12, 8, 24, 28]:
            fo = len(data) - footer_size
            n = footer_size // 4
            vals = struct.unpack_from(f'<{n}I', data, fo)
            valid = all(v < len(data) for v in vals)
            print(f"  Alt footer {footer_size} bytes: {vals} valid={valid}")
        
        # Try treating the string data as starting from the first string occurrence
        # Search for the first .NET string in the data
        print("\n  === Scanning for .NET format strings ===")
        return scan_for_strings_and_handlers(data)
    
    # Parse string table
    strings_offset = offsets[4]
    print(f"\n  === String Table (at offset {strings_offset}) ===")
    strings = parse_string_table(data, strings_offset, footer_offset)
    
    # Parse reference frames
    frames_offset = offsets[1]
    disposed_offset = offsets[2]
    print(f"\n  === Reference Frames (at offset {frames_offset}) ===")
    parse_reference_frames(data, frames_offset, disposed_offset, strings)
    
    return strings


def parse_string_table(data, start, end):
    """Parse the string table section."""
    pos = start
    count = struct.unpack_from('<I', data, pos)[0]
    pos += 4
    print(f"  String count: {count}")
    
    strings = []
    for i in range(min(count, 500)):  # Safety limit
        if pos >= end:
            break
        text, new_pos = read_dotnet_string(data, pos)
        if text is None:
            break
        strings.append(text)
        if len(text) < 100:  # Only print short strings
            print(f"    [{i}] = {repr(text)}")
        else:
            print(f"    [{i}] = {repr(text[:80])}... ({len(text)} chars)")
        pos = new_pos
    
    return strings


def parse_reference_frames(data, start, end, strings):
    """Parse reference frames section (20 bytes per frame)."""
    pos = start
    count = struct.unpack_from('<I', data, pos)[0]
    pos += 4
    print(f"  Frame count: {count}")
    
    frame_size = 20  # Each frame is 20 bytes
    
    event_handlers = []
    
    for i in range(min(count, 1000)):  # Safety limit
        if pos + frame_size > end:
            break
        
        frame_type, d1, d2 = struct.unpack_from('<III', data, pos)
        d3, d4 = struct.unpack_from('<II', data, pos + 12)
        event_handler_id = struct.unpack_from('<Q', data, pos + 12)[0]  # Int64
        
        if frame_type == 1:  # Element
            elem_name = strings[d2] if d2 < len(strings) else f"?{d2}"
            subtree = d1
            print(f"    [{i}] Element: <{elem_name}> subtree={subtree}")
        elif frame_type == 2:  # Text
            text = strings[d1] if d1 < len(strings) else f"?{d1}"
            if text and not text.startswith('\n'):
                print(f"    [{i}] Text: {repr(text[:80])}")
        elif frame_type == 3:  # Attribute
            attr_name = strings[d1] if d1 < len(strings) else f"?{d1}"
            attr_value = strings[d2] if d2 < len(strings) else f"?{d2}"
            if event_handler_id > 0:
                print(f"    [{i}] Attribute: {attr_name}={repr(attr_value[:50] if attr_value else '')} eventHandlerId={event_handler_id}")
                event_handlers.append((event_handler_id, attr_name, attr_value))
            elif attr_name in ('class', 'onclick', 'type'):
                print(f"    [{i}] Attribute: {attr_name}={repr(attr_value[:80] if attr_value else '')}")
        elif frame_type == 4:  # Component
            subtree = d1
            comp_id = d2
            print(f"    [{i}] Component: id={comp_id} subtree={subtree}")
        elif frame_type == 5:  # Region
            subtree = d1
            #print(f"    [{i}] Region: subtree={subtree}")
        elif frame_type == 8:  # Markup
            markup = strings[d1] if d1 < len(strings) else f"?{d1}"
            if markup and len(markup) > 0:
                print(f"    [{i}] Markup: {repr(markup[:80])}")
        
        pos += frame_size
    
    if event_handlers:
        print(f"\n  === EVENT HANDLERS ===")
        for eid, name, value in event_handlers:
            print(f"    eventHandlerId={eid}, event={name}, value={repr(value[:80] if value else '')}")
    
    return event_handlers


def scan_for_strings_and_handlers(data):
    """Fallback: scan binary data for strings and try to find event handler IDs near onclick."""
    text = data.decode('utf-8', errors='replace')
    
    # Find all .NET encoded strings by looking for patterns
    print("  Looking for onclick events and nearby Int64 values...")
    
    for search in ['onclick']:
        idx = 0
        while True:
            idx = text.find(search, idx)
            if idx < 0:
                break
            
            # Look at the 20 bytes before and after
            before_start = max(0, idx - 20)
            after_end = min(len(data), idx + len(search) + 20)
            
            hex_before = data[before_start:idx].hex()
            hex_after = data[idx + len(search):after_end].hex()
            
            # Try reading Int64 values from various offsets near this position
            for offset in range(-16, 20, 4):
                try_pos = idx + offset
                if 0 <= try_pos and try_pos + 8 <= len(data):
                    val = struct.unpack_from('<Q', data, try_pos)[0]
                    if 0 < val < 10000:
                        print(f"    Potential eventHandlerId={val} at offset {try_pos} (relative to onclick at {idx}: {offset:+d})")
            
            idx += len(search)


async def main():
    base = 'http://192.168.2.70'
    session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar())

    # 1. Load /wallbox HTML
    async with session.get(f'{base}/wallbox') as resp:
        html = await resp.text()
    comps = extract_components(html)
    app_state = extract_app_state(html)
    print(f'Components: {len(comps)}')

    # 2. Negotiate
    async with session.post(f'{base}/_blazor/negotiate?negotiateVersion=1', data='') as resp:
        neg = await resp.json()
        token = neg['connectionToken']

    # 3. WebSocket
    ws = await session.ws_connect(f'ws://192.168.2.70/_blazor?id={token}')
    await ws.send_str('{"protocol":"blazorpack","version":1}\x1e')
    msg = await ws.receive()
    print('Handshake OK')

    # 4. Start circuit for /wallbox
    start_msg = [1, {}, '0', 'StartCircuit', [base + '/', base + '/wallbox', '[]', app_state]]
    await ws.send_bytes(encode_message(start_msg))
    await asyncio.sleep(0.3)

    # 5. UpdateRootComponents
    ops = []
    for i, cd in enumerate(comps):
        ops.append({
            'type': 'add', 'ssrComponentId': i + 1,
            'marker': {
                'type': cd['type'], 'prerenderId': cd.get('prerenderId', ''),
                'key': cd.get('key', {}), 'sequence': cd.get('sequence', 0),
                'descriptor': cd.get('descriptor', ''), 'uniqueId': i
            }
        })
    batch_json = json.dumps({'batchId': 1, 'operations': ops})
    upd_msg = [1, {}, None, 'UpdateRootComponents', [batch_json, app_state]]
    await ws.send_bytes(encode_message(upd_msg))

    # 6. Collect render batches
    render_batches = []
    for _ in range(40):
        try:
            msg = await asyncio.wait_for(ws.receive(), timeout=1.0)
            if msg.type == aiohttp.WSMsgType.BINARY:
                messages = decode_messages(msg.data)
                for m in messages:
                    if len(m) >= 5 and m[0] == 1:
                        target = m[3] if len(m) > 3 else None
                        args = m[4] if len(m) > 4 else []
                        if target == 'JS.RenderBatch':
                            batch_id = args[0] if args else None
                            batch_data = args[1] if len(args) > 1 else None
                            data_len = len(batch_data) if batch_data else 0
                            print(f'\nRenderBatch id={batch_id}, len={data_len}')
                            render_batches.append((batch_id, batch_data))
                            ack = [1, {}, None, 'OnRenderCompleted', [batch_id, None]]
                            await ws.send_bytes(encode_message(ack))
                        elif target == 'JS.BeginInvokeJS':
                            task_id = args[0] if args else 0
                            result_json = f'[{task_id},true,null]'
                            ack = [1, {}, None, 'EndInvokeJSFromDotNet', [task_id, True, result_json]]
                            await ws.send_bytes(encode_message(ack))
        except asyncio.TimeoutError:
            continue

    # 7. Parse the main render batch (batch 4 = largest initial one)
    print(f'\n{"="*60}')
    print(f'PARSING RENDER BATCHES')
    print(f'{"="*60}')
    
    for batch_id, batch_data in render_batches:
        if not batch_data or not isinstance(batch_data, bytes):
            continue
        if len(batch_data) < 500:
            continue  # Skip small batches
        
        print(f'\n--- Batch {batch_id} ({len(batch_data)} bytes) ---')
        parse_render_batch(batch_data)

    # Also save the largest batch for offline analysis
    largest = max(render_batches, key=lambda x: len(x[1]) if x[1] and isinstance(x[1], bytes) else 0)
    with open('scripts/wallbox_batch_dump.bin', 'wb') as f:
        f.write(largest[1])
    print(f'\nSaved largest batch ({len(largest[1])} bytes) to scripts/wallbox_batch_dump.bin')

    await ws.close()
    await session.close()


if __name__ == '__main__':
    asyncio.run(main())
