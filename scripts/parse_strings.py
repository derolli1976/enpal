"""Focused parser for Blazor RenderBatch - resolve string table to map event handler IDs to button labels."""
import struct
import sys


def read_int32s(data, offset, count):
    """Read count Int32 values from data at offset."""
    return struct.unpack_from(f'<{count}I', data, offset)


def main():
    with open('scripts/wallbox_batch_dump.bin', 'rb') as f:
        # Read batch 3 (18448 bytes - the largest)
        data3 = f.read()
    
    print(f"Batch 3 size: {len(data3)} bytes")
    
    # Read batch 4 separately - we need to capture it
    # For now, let's work with what we have
    
    # Parse the footer (last 20 bytes)
    footer = struct.unpack_from('<5I', data3, len(data3) - 20)
    print(f"Footer: updComp={footer[0]}, refFrames={footer[1]}, dispComp={footer[2]}, dispEvt={footer[3]}, strings={footer[4]}")
    
    strings_offset = footer[4]
    ref_frames_offset = footer[1]
    disp_comp_offset = footer[2]
    
    # The strings section format from ASP.NET Core WebRenderBatchWriter.cs:
    # [Int32: count]
    # For each string:
    #   [Int32: byteLength] (or -1 for null)
    #   [byteLength bytes: UTF-8 data]
    
    print(f"\n=== String Table at offset {strings_offset} ===")
    pos = strings_offset
    str_count = struct.unpack_from('<i', data3, pos)[0]
    pos += 4
    print(f"String count: {str_count}")
    
    # Parse strings
    strings = []
    end = len(data3) - 20  # Before footer
    for i in range(str_count):
        if pos >= end:
            print(f"  Ran out of data at string {i}")
            break
        strlen = struct.unpack_from('<i', data3, pos)[0]
        pos += 4
        if strlen == -1:
            strings.append(None)
        elif strlen >= 0 and strlen < 10000:  # Sanity check
            if pos + strlen > end:
                print(f"  String {i} overflows at pos {pos}, len {strlen}")
                break
            text = data3[pos:pos + strlen].decode('utf-8', errors='replace')
            strings.append(text)
            pos += strlen
        else:
            print(f"  Invalid string length {strlen} at string {i}, pos {pos}")
            # Try interpreting as something else
            break
    
    print(f"Parsed {len(strings)} strings")
    
    # Print interesting strings
    for i, s in enumerate(strings):
        if s and len(s) > 0 and len(s) < 200:
            # Filter for interesting ones
            if any(kw in s.lower() for kw in ['start', 'stop', 'eco', 'full', 'solar', 'smart', 'mode', 'status',
                                                'charg', 'connect', 'click', 'button', 'wallbox']):
                print(f"  [{i}] = {repr(s)}")
    
    print(f"\n=== Reference Frames at offset {ref_frames_offset} ===")
    pos = ref_frames_offset
    frame_count = struct.unpack_from('<I', data3, pos)[0]
    pos += 4
    print(f"Frame count: {frame_count}")
    
    frame_size = 20
    for i in range(frame_count):
        if pos + frame_size > disp_comp_offset:
            break
        ft, d1, d2, d3lo, d3hi = struct.unpack_from('<IIIII', data3, pos)
        event_id = struct.unpack_from('<Q', data3, pos + 12)[0]
        
        def s(idx):
            if idx < len(strings) and strings[idx] is not None:
                return strings[idx]
            return f'?{idx}'
        
        if ft == 1:  # Element
            print(f"  [{i}] Element: <{s(d2)}> subtree={d1}")
        elif ft == 2:  # Text
            text = s(d1)
            if text and not text.startswith('\n') and not text.startswith('?'):
                print(f"  [{i}] Text: {repr(text[:100])}")
            elif text and text.startswith('?'):
                print(f"  [{i}] Text: {text}")
        elif ft == 3:  # Attribute
            if event_id > 0:
                print(f"  [{i}] Attribute: {s(d1)}={repr(s(d2)[:80])} ** eventHandlerId={event_id} **")
            elif s(d1) in ('class', 'onclick', 'type', '__internal_stopPropagation_onclick'):
                print(f"  [{i}] Attribute: {s(d1)}={repr(s(d2)[:120])}")
        elif ft == 4:  # Component
            print(f"  [{i}] Component: id={d2} subtree={d1}")
        elif ft == 8:  # Markup
            markup = s(d1)
            if markup and not markup.startswith('?') and len(markup) > 0:
                print(f"  [{i}] Markup: {repr(markup[:100])}")
        
        pos += frame_size


if __name__ == '__main__':
    main()
