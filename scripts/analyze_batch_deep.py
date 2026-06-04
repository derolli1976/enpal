"""Deep analysis of saved RenderBatch binary dump."""
import struct


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
    if length < 0 or length > 5000 or pos + length > len(data):
        return None, offset
    text = data[pos:pos + length].decode('utf-8', errors='replace')
    return text, pos + length


def main():
    with open('scripts/wallbox_batch_dump.bin', 'rb') as f:
        data = f.read()

    print(f"Total: {len(data)} bytes")

    # Footer
    footer_offset = len(data) - 20
    offsets = struct.unpack_from('<5I', data, footer_offset)
    print(f"Footer: {offsets}")

    # Try reading strings from offset 4988 (after disposed event count=0)
    print(f"\n=== Strings starting at offset 4988 ===")
    pos = 4988
    strings = []
    for i in range(300):
        if pos >= len(data) - 20:
            break
        text, new_pos = read_dotnet_string(data, pos)
        if text is None:
            print(f"  [{i}] Bad string at offset {pos}, stopping")
            break
        strings.append(text)
        if i < 150 and len(text) < 120:
            print(f"  [{i}] = {repr(text)}")
        elif i < 150:
            print(f"  [{i}] = {repr(text[:80])}... ({len(text)} chars)")
        pos = new_pos

    print(f"\nTotal strings: {len(strings)}")
    print(f"Ended at offset: {pos}")

    # Now re-parse reference frames
    frames_offset = offsets[1]
    disposed_offset = offsets[2]
    pos = frames_offset
    frame_count = struct.unpack_from('<I', data, pos)[0]
    pos += 4
    print(f"\n=== Reference Frames: {frame_count} frames ===")

    frame_size = 20
    event_handlers = []
    for i in range(frame_count):
        if pos + frame_size > disposed_offset:
            break
        frame_type = struct.unpack_from('<I', data, pos)[0]
        d1 = struct.unpack_from('<I', data, pos + 4)[0]
        d2 = struct.unpack_from('<I', data, pos + 8)[0]
        event_id = struct.unpack_from('<Q', data, pos + 12)[0]

        safe_str = lambda idx: strings[idx] if idx < len(strings) else f"?{idx}"

        if frame_type == 1:  # Element
            print(f"  [{i}] Element: <{safe_str(d2)}>  subtree_len={d1}")
        elif frame_type == 2:  # Text
            t = safe_str(d1)
            if t.strip():
                print(f"  [{i}] Text: {repr(t[:80])}")
        elif frame_type == 3:  # Attribute
            attr = safe_str(d1)
            val = "" if d2 == 0xFFFFFFFF else safe_str(d2)
            if event_id > 0:
                event_handlers.append((event_id, attr, i))
                print(f"  [{i}] Attr: {attr} handler={event_id}")
            elif attr in ('onclick', 'onchange', 'class', 'type', 'href', 'style') or 'btn' in str(val).lower():
                print(f"  [{i}] Attr: {attr}={repr(str(val)[:60])}")
        elif frame_type == 4:  # Component
            print(f"  [{i}] Component: id={d2} subtree_len={d1}")
        elif frame_type == 8:  # Markup
            mk = safe_str(d1)
            if mk.strip():
                print(f"  [{i}] Markup: {repr(mk[:80])}")
        else:
            print(f"  [{i}] Unknown type={frame_type}: d1={d1}, d2={d2}, evtId={event_id}")

        pos += frame_size

    print(f"\n=== Event Handlers Found ===")
    for eid, attr, frame_idx in event_handlers:
        print(f"  handler={eid}, event={attr}, frame={frame_idx}")

    # Map handlers to button labels by looking at nearby text frames
    print(f"\n=== Handler-to-Label Mapping ===")
    # Re-parse to collect ALL frames in order
    pos = frames_offset + 4
    all_frames = []
    for i in range(frame_count):
        if pos + frame_size > disposed_offset:
            break
        ft = struct.unpack_from('<I', data, pos)[0]
        d1 = struct.unpack_from('<I', data, pos + 4)[0]
        d2 = struct.unpack_from('<I', data, pos + 8)[0]
        eid = struct.unpack_from('<Q', data, pos + 12)[0]
        all_frames.append((ft, d1, d2, eid))
        pos += frame_size

    for eid, attr, frame_idx in event_handlers:
        # Look forward from this frame for the nearest text frame
        for j in range(frame_idx + 1, min(frame_idx + 5, len(all_frames))):
            ft2, d1_2, d2_2, _ = all_frames[j]
            if ft2 == 2:  # Text frame
                label = strings[d1_2] if d1_2 < len(strings) else f"?{d1_2}"
                if label.strip():
                    print(f"  handler={eid} ({attr}) -> label={repr(label)}")
                    break


if __name__ == '__main__':
    main()
