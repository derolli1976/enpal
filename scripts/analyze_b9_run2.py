"""Follow-up analysis: click results, attachWebRendererInterop refs, sensor rows after clicks."""
import json, sys, base64, importlib.util
from collections import Counter

spec = importlib.util.spec_from_file_location(
    "rb", r"custom_components/enpal_webparser/api/render_batch.py")
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)

p = sys.argv[1]
events = [json.loads(l) for l in open(p, encoding="utf-8")]

# 1) All ws_binary entries that carry a toggle result.
n_ok = n_fail = 0
fail_msgs = Counter()
for e in events:
    if e["type"] == "ws_binary" and "toggle_dom_id" in e:
        if e.get("toggle_success"):
            n_ok += 1
            print(f"[{e['elapsed']:>8}] OK {e['toggle_dom_id']}")
        else:
            n_fail += 1
print(f"click results: {n_ok} OK, {n_fail} FAILED")

# 2) Find the error payloads of failed EndInvokeDotNet (stored in messages?).
shown = 0
for e in events:
    if e["type"] != "ws_binary":
        continue
    for m in e.get("messages", []):
        t = m.get("target") or ""
        if t == "JS.EndInvokeDotNet" and shown < 3:
            print(f"[{e['elapsed']:>8}] EndInvokeDotNet args={json.dumps(m.get('arguments'))[:400]}")
            shown += 1

# 3) attachWebRendererInterop / __dotNetObject refs seen.
for e in events:
    if e["type"] != "ws_binary":
        continue
    for m in e.get("messages", []):
        t = m.get("target") or ""
        args = json.dumps(m.get("arguments", ""))[:200]
        if "attachWebRendererInterop" in args or "__dotNetObject" in args:
            print(f"[{e['elapsed']:>8}] target={t} args={args}")

# 4) Did ANY scrape_diff contain new (hidden) rows e.g. Charge.Level?
hits = 0
for e in events:
    if e["type"] == "scrape_diff":
        txt = json.dumps(e)
        if "Charge.Level" in txt:
            hits += 1
            if hits <= 3:
                print(f"[{e['elapsed']:>8}] scrape_diff contains Charge.Level")
print(f"scrape_diffs mentioning Charge.Level: {hits}")

# 5) Render batch cadence: how often, before vs after clicking started (t=10)?
rb_times = [e["elapsed"] for e in events if e["type"] == "ws_binary"
            and any(m.get("render_batch_payload_b64") for m in e.get("messages", []))]
before = [t for t in rb_times if t < 10]
after = [t for t in rb_times if t >= 10]
print(f"render batches: {len(before)} before t=10, {len(after)} after; "
      f"run end at t={events[-1]['elapsed']}")
