"""Analyze the /wallbox Blazor page to understand RenderBatch structure."""
import asyncio
import aiohttp
import json
import msgpack
import io
import re
import sys
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
    hs = msg.data if isinstance(msg.data, str) else msg.data.decode('utf-8')
    print(f'Handshake: {hs[:80]}...')

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

    # 6. Read messages for ~8 seconds, collect all binary data
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
                            print(f'\nRenderBatch id={batch_id}, data type={type(batch_data).__name__}, len={data_len}')
                            render_batches.append((batch_id, batch_data))
                            # Acknowledge
                            ack = [1, {}, None, 'OnRenderCompleted', [batch_id, None]]
                            await ws.send_bytes(encode_message(ack))
                        elif target == 'JS.BeginInvokeJS':
                            task_id = args[0] if args else 0
                            identifier = args[1] if len(args) > 1 else '?'
                            call_args = args[2] if len(args) > 2 else '?'
                            print(f'JS.BeginInvokeJS task={task_id}, id={identifier}, args={str(call_args)[:200]}')
                            result_json = f'[{task_id},true,null]'
                            ack = [1, {}, None, 'EndInvokeJSFromDotNet', [task_id, True, result_json]]
                            await ws.send_bytes(encode_message(ack))
                        else:
                            print(f'Other: target={target}, args_len={len(args)}')
        except asyncio.TimeoutError:
            continue

    # 7. Analyze render batch data
    print(f'\n=== ANALYSIS: {len(render_batches)} RenderBatch(es) ===')
    for batch_id, batch_data in render_batches:
        if not batch_data:
            continue
        
        if isinstance(batch_data, bytes):
            raw = batch_data
        elif isinstance(batch_data, str):
            raw = batch_data.encode('utf-8')
        else:
            print(f'  Batch {batch_id}: unexpected type {type(batch_data)}')
            continue
        
        print(f'\n--- Batch {batch_id} ({len(raw)} bytes) ---')
        
        # Search for known text strings in raw bytes
        text = raw.decode('utf-8', errors='replace')
        for search in ['Start', 'Stop', 'Eco', 'Full', 'Solar', 'Smart', 'Mode', 'Status', 
                       'Charging', 'Connected', 'wallbox', 'Wallbox', 'onclick', 'click',
                       'button', 'Button', 'MudButton', 'Start/Stop', 'Charge Mode',
                       'START', 'STOP', 'SET']:
            idx = 0
            while True:
                idx = text.find(search, idx)
                if idx < 0:
                    break
                start = max(0, idx - 40)
                end = min(len(text), idx + len(search) + 40)
                snippet = repr(text[start:end])
                print(f'  Found "{search}" at offset {idx}: {snippet}')
                
                # Also show hex of surrounding bytes for event handler IDs
                hex_start = max(0, idx - 20)
                hex_end = min(len(raw), idx + len(search) + 20)
                hex_bytes = raw[hex_start:hex_end].hex()
                print(f'    hex: {hex_bytes}')
                
                idx += len(search)
        
        # Also look for int32 patterns that could be event handler IDs
        # Blazor typically uses small positive integers
        print(f'\n  First 200 bytes hex: {raw[:200].hex()}')
        print(f'  Last 100 bytes hex: {raw[-100:].hex()}')

    await ws.close()
    await session.close()


if __name__ == '__main__':
    asyncio.run(main())
