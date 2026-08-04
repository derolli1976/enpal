"""One-off: replay Graib's sniffer JSONL through the position-based toggle mapping.

Validates that the ids mapped by position for batch N are exactly the ids the
box disposes later (i.e. we would always have clicked a live handler).
"""
import json, base64, struct, sys, importlib.util

spec = importlib.util.spec_from_file_location(
    "rb", r"custom_components/enpal_webparser/api/render_batch.py")
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)

TOGGLE_PREFIXES = ("showUnsupported_", "showInternal_")


def disposed_ids(raw):
    f = struct.unpack_from("<5i", raw, len(raw) - 20)
    pos = f[3]
    if not (0 <= pos < len(raw) - 4):
        return []
    cnt = struct.unpack_from("<i", raw, pos)[0]
    if cnt <= 0 or cnt > 10000:
        return []
    return list(struct.unpack_from(f"<{cnt}q", raw, pos + 4))


p = sys.argv[1]
positions = {}
count = 0
current = {}  # dom_id -> mapped handler id (freshest known)
history = []  # (elapsed, dom_id -> id) snapshots
all_disposed = set()

for line in open(p, encoding="utf-8"):
    e = json.loads(line)
    if e["type"] != "ws_binary":
        continue
    for m in e.get("messages", []):
        b64 = m.get("render_batch_payload_b64")
        if not b64:
            continue
        raw = base64.b64decode(b64)
        all_disposed.update(disposed_ids(raw))
        ordered = rb.extract_change_handler_ids(raw)
        named = {d: h for d, h in rb.extract_event_handlers(raw).items()
                 if d.startswith(TOGGLE_PREFIXES)}
        if named:
            eid_to_pos = {eid: i for i, eid in enumerate(ordered)}
            count = len(ordered)
            positions = {d: eid_to_pos[h] for d, h in named.items() if h in eid_to_pos}
            current.update(named)
            print(f"[{e['elapsed']:>8}] initial batch: {len(positions)} positions, "
                  f"{count} change handlers")
        elif positions and ordered and len(ordered) == count:
            for d, pos_ in positions.items():
                current[d] = ordered[pos_]
        if current:
            history.append((e["elapsed"], dict(current)))

print(f"\nbatches with mapping: {len(history)}")
print("last mapping:", history[-1][1])

# Validate: every mapped id must eventually appear in a disposed list
# (proving it was a real live handler), except the very last generation.
last_gen = set(history[-1][1].values())
bad = 0
for elapsed, snap in history:
    for d, eid in snap.items():
        if eid not in all_disposed and eid not in last_gen:
            print(f"  UNEXPECTED: {d} id {eid} at {elapsed} never disposed")
            bad += 1
print(f"\nvalidation: {'OK - all mapped ids were live handler generations' if bad == 0 else f'{bad} mismatches'}")

# Show what would have been clicked at Graib's click times (11.078 etc.)
for t in (11.078, 12.826, 15.966, 17.735):
    snap = None
    for elapsed, s in history:
        if elapsed <= t:
            snap = s
    if snap:
        print(f"at t={t}: showUnsupported_Battery would use id {snap.get('showUnsupported_Battery')}")
