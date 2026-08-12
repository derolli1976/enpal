"""One-off: check Graib's sniffer JSONL for disposed event handler ids."""
import json, base64, struct, sys

p = sys.argv[1]
for line in open(p, encoding="utf-8"):
    e = json.loads(line)
    if e["type"] != "ws_binary":
        continue
    for m in e.get("messages", []):
        b64 = m.get("render_batch_payload_b64")
        if not b64:
            continue
        raw = base64.b64decode(b64)
        if len(raw) < 24:
            continue
        f = struct.unpack_from("<5i", raw, len(raw) - 20)
        # sections: updatedComponents, referenceFrames, disposedComponentIds,
        # disposedEventHandlerIds, strings
        pos = f[3]
        if not (0 <= pos < len(raw) - 4):
            continue
        cnt = struct.unpack_from("<i", raw, pos)[0]
        if cnt <= 0 or cnt > 10000:
            continue
        ids = list(struct.unpack_from(f"<{cnt}q", raw, pos + 4))
        tail = "..." if cnt > 20 else ""
        print(f"elapsed={e['elapsed']:>8} frame={e['frame']:>3} "
              f"batch={m.get('render_batch_id')} disposed={ids[:20]}{tail} ({cnt})")
