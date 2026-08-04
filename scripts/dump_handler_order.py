"""One-off: ordered list of event-handler attributes in the initial RenderBatch."""
import json, base64, struct, sys, importlib.util

spec = importlib.util.spec_from_file_location(
    "rb", r"custom_components/enpal_webparser/api/render_batch.py")
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)

p = sys.argv[1]
payload = None
for line in open(p, encoding="utf-8"):
    e = json.loads(line)
    if e["type"] != "ws_binary":
        continue
    for m in e.get("messages", []):
        b64 = m.get("render_batch_payload_b64")
        if b64 and m.get("render_batch_payload_bytes", 0) > 20000:
            payload = base64.b64decode(b64)
            break
    if payload:
        break

raw = payload
strings = rb.parse_render_batch_strings(raw)
footer = struct.unpack_from("<5i", raw, len(raw) - 20)
pos, frames_end = footer[1], footer[2]
count = struct.unpack_from("<i", raw, pos)[0]
pos += 4

current_id = None
order = 0
for _ in range(count):
    if pos + 20 > frames_end:
        break
    ft, a, b = struct.unpack_from("<iii", raw, pos)
    eid = struct.unpack_from("<q", raw, pos + 12)[0]
    if ft == 3:
        name = strings[a] if 0 <= a < len(strings) else None
        val = strings[b] if 0 <= b < len(strings) else None
        if name == "id":
            current_id = val
        if eid > 0:
            print(f"#{order:2d} eid={eid:4d} attr={name!r:12} id={current_id!r}")
            order += 1
    else:
        current_id = None
    pos += 20
