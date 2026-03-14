"""Test clicking a wallbox button via Blazor SignalR protocol.
Safe test: sends "Set Eco" which matches the current mode - no state change.
"""
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


def find_onclick_handlers(batch_data):
    """Find onclick event handler IDs from RenderBatch frame data.
    
    Returns list of event handler IDs in the order they appear in the DOM.
    """
    if len(batch_data) < 24:
        return []
    
    # Read footer
    footer = struct.unpack_from('<5I', batch_data, len(batch_data) - 20)
    ref_frames_offset = footer[1]
    disp_comp_offset = footer[2]
    
    if ref_frames_offset >= len(batch_data) or disp_comp_offset >= len(batch_data):
        return []
    
    # Parse reference frames (20 bytes each)
    pos = ref_frames_offset
    frame_count = struct.unpack_from('<I', batch_data, pos)[0]
    pos += 4
    
    handlers = []
    frame_size = 20
    for i in range(frame_count):
        if pos + frame_size > disp_comp_offset:
            break
        ft = struct.unpack_from('<I', batch_data, pos)[0]
        if ft == 3:  # Attribute frame
            event_id = struct.unpack_from('<Q', batch_data, pos + 12)[0]
            if event_id > 0:
                handlers.append(event_id)
        pos += frame_size
    
    return handlers


def extract_status_from_batch(batch_data):
    """Search batch data for 'Mode X' and 'Status Y' text patterns."""
    text = batch_data.decode('utf-8', errors='replace')
    
    mode = None
    status = None
    
    # Look for "Mode " followed by a short string
    mode_patterns = [
        (r'Mode\s+(\w+)', 'mode'),
    ]
    
    # Search for pattern: length_byte + "Mode " + length_byte + value
    # BinaryWriter format: \x05Mode \x03Eco
    idx = 0
    while True:
        idx = text.find('Mode ', idx)
        if idx < 0:
            break
        # Check if this is followed by a short word
        after = text[idx + 5:idx + 30]
        # Find the next word (the mode value)
        word = ''
        for c in after:
            if c.isalpha():
                word += c
            elif word:
                break
        if word and word not in ('Eco', 'Solar', 'Full', 'Smart', 'Fast'):
            idx += 5
            continue
        if word:
            mode = word
            break
        idx += 5
    
    # Search for "Status " followed by a short string
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


async def main():
    base = 'http://192.168.2.70'
    session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar())

    # 1. Load /wallbox HTML
    async with session.get(f'{base}/wallbox') as resp:
        html = await resp.text()
    comps = extract_components(html)
    app_state = extract_app_state(html)
    print(f'Components: {len(comps)}')

    # 2. Negotiate + WebSocket
    async with session.post(f'{base}/_blazor/negotiate?negotiateVersion=1', data='') as resp:
        neg = await resp.json()
        token = neg['connectionToken']
    
    ws = await session.ws_connect(f'ws://192.168.2.70/_blazor?id={token}')
    await ws.send_str('{"protocol":"blazorpack","version":1}\x1e')
    await ws.receive()  # Handshake response
    print('Handshake OK')

    # 3. Start circuit
    start_msg = [1, {}, '0', 'StartCircuit', [base + '/', base + '/wallbox', '[]', app_state]]
    await ws.send_bytes(encode_message(start_msg))
    await asyncio.sleep(0.3)

    # 4. UpdateRootComponents
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

    # 5. Receive initial batches and find onclick handlers
    all_handlers = []
    mode = None
    status = None
    invocation_id = 100
    
    for _ in range(30):
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
                            if batch_data and isinstance(batch_data, bytes):
                                handlers = find_onclick_handlers(batch_data)
                                if handlers:
                                    all_handlers.extend(handlers)
                                    print(f'  Batch {batch_id}: found {len(handlers)} onclick handlers: {handlers}')
                                
                                # Extract status
                                m_mode, m_status = extract_status_from_batch(batch_data)
                                if m_mode:
                                    mode = m_mode
                                if m_status:
                                    status = m_status
                                
                                # Save batch 4 for analysis
                                if len(batch_data) > 5000:
                                    with open('scripts/wallbox_batch4_dump.bin', 'wb') as f:
                                        f.write(batch_data)
                            
                            ack = [1, {}, None, 'OnRenderCompleted', [batch_id, None]]
                            await ws.send_bytes(encode_message(ack))
                        elif target == 'JS.BeginInvokeJS':
                            task_id = args[0] if args else 0
                            result_json = f'[{task_id},true,null]'
                            ack = [1, {}, None, 'EndInvokeJSFromDotNet', [task_id, True, result_json]]
                            await ws.send_bytes(encode_message(ack))
        except asyncio.TimeoutError:
            continue
    
    print(f'\nTotal onclick handlers found: {all_handlers}')
    print(f'Mode: {mode}, Status: {status}')
    
    if not all_handlers:
        print('ERROR: No onclick handlers found!')
        await ws.close()
        await session.close()
        return
    
    # Map handlers to buttons based on DOM order
    # Expected order: [nav_toggle?, ..., Start, Stop, Eco, Full, Solar, Smart]
    # The last 6 handlers should be the wallbox buttons
    if len(all_handlers) >= 6:
        wallbox_handlers = all_handlers[-6:]
        button_map = {
            'start': wallbox_handlers[0],
            'stop': wallbox_handlers[1],
            'eco': wallbox_handlers[2],
            'full': wallbox_handlers[3],
            'solar': wallbox_handlers[4],
            'smart': wallbox_handlers[5],
        }
        print(f'\nWallbox button mapping:')
        for name, hid in button_map.items():
            print(f'  {name}: eventHandlerId={hid}')
    else:
        print(f'WARNING: Expected 6+ handlers, got {len(all_handlers)}')
        button_map = {}
    
    # 6. Test: Click "Set Eco" (safe - already in Eco mode)
    if 'eco' in button_map:
        eco_handler = button_map['eco']
        print(f'\n=== TESTING: Clicking "Set Eco" button (handler {eco_handler}) ===')
        
        invocation_id += 1
        event_descriptor = json.dumps({
            "browserRendererId": 0,
            "eventHandlerId": eco_handler,
            "eventName": "click",
            "eventFieldInfo": None
        })
        event_args = json.dumps({
            "type": "click",
            "detail": 1,
            "screenX": 0,
            "screenY": 0,
            "clientX": 0,
            "clientY": 0,
            "button": 0,
            "buttons": 0,
            "ctrlKey": False,
            "shiftKey": False,
            "altKey": False,
            "metaKey": False
        })
        
        click_msg = [1, {}, str(invocation_id), "DispatchBrowserEvent", [event_descriptor, event_args]]
        await ws.send_bytes(encode_message(click_msg))
        print(f'  Sent click event')
        
        # Wait for response
        click_response = False
        for _ in range(10):
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=2.0)
                if msg.type == aiohttp.WSMsgType.BINARY:
                    messages = decode_messages(msg.data)
                    for m in messages:
                        if len(m) >= 4 and m[0] == 1:
                            target = m[3] if len(m) > 3 else None
                            args_data = m[4] if len(m) > 4 else []
                            if target == 'JS.RenderBatch':
                                batch_id = args_data[0]
                                batch_data = args_data[1] if len(args_data) > 1 else None
                                print(f'  Got RenderBatch {batch_id} ({len(batch_data) if batch_data else 0} bytes) -> CLICK WORKED!')
                                click_response = True
                                
                                if batch_data:
                                    m_mode, m_status = extract_status_from_batch(batch_data)
                                    if m_mode:
                                        print(f'  Updated Mode: {m_mode}')
                                    if m_status:
                                        print(f'  Updated Status: {m_status}')
                                
                                ack = [1, {}, None, 'OnRenderCompleted', [batch_id, None]]
                                await ws.send_bytes(encode_message(ack))
                            elif target == 'JS.BeginInvokeJS':
                                task_id = args_data[0] if args_data else 0
                                result_json = f'[{task_id},true,null]'
                                ack = [1, {}, None, 'EndInvokeJSFromDotNet', [task_id, True, result_json]]
                                await ws.send_bytes(encode_message(ack))
                            else:
                                print(f'  Response: {target}')
                elif msg.type == aiohttp.WSMsgType.TEXT:
                    print(f'  Text response: {msg.data[:200]}')
            except asyncio.TimeoutError:
                if click_response:
                    break
                continue
        
        if not click_response:
            print('  No RenderBatch response - click may have failed')
    
    await ws.close()
    await session.close()
    print('\nDone!')


if __name__ == '__main__':
    asyncio.run(main())
