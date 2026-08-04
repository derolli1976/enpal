"""One-off: dump reference frames of a mid-stream RenderBatch from the sniffer JSONL."""
import json, base64, struct, sys, importlib.util

spec = importlib.util.spec_from_file_location(
    "rb", r"custom_components/enpal_webparser/api/render_batch.py")
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)

p = sys.argv[1]
want_frame = int(sys.argv[2])

payload = None
for line in open(p, encoding="utf-8"):
    e = json.loads(line)
    if e["type"] != "ws_binary" or e["frame"] != want_frame:
        continue
    for m in e.get("messages", []):
        b64 = m.get("render_batch_payload_b64")
        if b64:
            payload = base64.b64decode(b64)
            break

raw = payload
print("bytes:", len(raw))
strings = rb.parse_render_batch_strings(raw)
print("strings:", len(strings))
footer = struct.unpack_from("<5i", raw, len(raw) - 20)
print("footer:", footer)
pos, frames_end = footer[1], footer[2]
count = struct.unpack_from("<i", raw, pos)[0]
pos += 4
print("frame count:", count)


def s(i):
    return strings[i] if 0 <= i < len(strings) else f"<{i}>"


out = 0
for n in range(count):
    if pos + 20 > frames_end or out > 200:
        break
    ft, a, b = struct.unpack_from("<iii", raw, pos)
    eid = struct.unpack_from("<q", raw, pos + 12)[0]
    if ft == 3:
        print(f"{n:4d} attr  name={s(a)!r:30} value={str(s(b))[:40]!r} eid={eid}")
    else:
        print(f"{n:4d} type={ft} a={a} b={b} q={eid}")
    out += 1
    pos += 20
