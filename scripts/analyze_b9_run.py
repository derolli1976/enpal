"""Analyze Graib's b9 sniffer run: what was clicked, with which ids, and why it failed."""
import json, sys, base64, struct, importlib.util

spec = importlib.util.spec_from_file_location(
    "rb", r"custom_components/enpal_webparser/api/render_batch.py")
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)

p = sys.argv[1]
events = [json.loads(l) for l in open(p, encoding="utf-8")]
print(f"total events: {len(events)}")
from collections import Counter
print(Counter(e["type"] for e in events))

# 1) toggle_handler events: did the position learning happen?
for e in events:
    if e["type"] == "toggle_handler":
        print(f"[{e['elapsed']:>8}] handler {e['dom_id']} id={e['handler_id']} pos={e.get('position')}")

print()
# 2) toggle_click events: which ids were used, when?
clicks = [e for e in events if e["type"] == "toggle_click"]
for e in clicks:
    print(f"[{e['elapsed']:>8}] CLICK {e['dom_id']} handler_id={e['handler_id']} call_id={e.get('call_id')} interop={e.get('renderer_interop_id')}")

print()
# 3) click results
for e in events:
    if e["type"] == "ws_binary" and e.get("toggle_dom_id"):
        print(f"[{e['elapsed']:>8}] RESULT {e['toggle_dom_id']} success={e['toggle_success']}")

print()
# 4) Reconstruct live handler generations around each click time.
def batches(ev):
    for m in ev.get("messages", []):
        b64 = m.get("render_batch_payload_b64")
        if b64:
            yield base64.b64decode(b64)

# Track: at each ws_binary with a render batch, the current live ordered onchange ids.
gen = []  # (elapsed, ordered list)
for e in events:
    if e["type"] != "ws_binary":
        continue
    for raw in batches(e):
        ordered = rb.extract_change_handler_ids(raw)
        if ordered:
            gen.append((e["elapsed"], ordered))

print(f"batches with onchange handlers: {len(gen)}")
if gen:
    print("first:", gen[0])
    print("counts:", Counter(len(o) for _, o in gen))

# For each click: was the used id inside the most recent generation before the click?
print()
for c in clicks:
    live = None
    for t, ordered in gen:
        if t <= c["elapsed"]:
            live = (t, ordered)
    if live:
        ok = c["handler_id"] in live[1]
        print(f"click {c['dom_id']} at {c['elapsed']}: id={c['handler_id']} "
              f"in live gen (t={live[0]}, ids {live[1][0]}..{live[1][-1]})? {ok}")

# 5) Any JS.Error / Close / circuit errors?
print()
for e in events:
    if e["type"] in ("ws_close", "js_error", "close_frame", "error"):
        print(f"[{e.get('elapsed','?'):>8}] {e['type']}: {str(e)[:300]}")
    if e["type"] == "ws_binary":
        for m in e.get("messages", []):
            t = m.get("target") or ""
            if "Error" in t or m.get("close"):
                print(f"[{e['elapsed']:>8}] msg target={t}: {str(m)[:200]}")
