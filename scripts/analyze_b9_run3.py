"""Dump raw EndInvokeDotNet / JS.Error entries and the full raw messages around clicks."""
import json, sys

p = sys.argv[1]
events = [json.loads(l) for l in open(p, encoding="utf-8")]

for e in events:
    if e["type"] != "ws_binary":
        continue
    for m in e.get("messages", []):
        t = m.get("target") or ""
        if t in ("JS.EndInvokeDotNet", "JS.Error"):
            print(f"[{e['elapsed']:>8}] {t}")
            print("   full message entry:", json.dumps(m)[:800])
            print()
            break
    else:
        continue
    if e["elapsed"] > 12:
        break

# Also count all targets seen
from collections import Counter
c = Counter()
for e in events:
    if e["type"] == "ws_binary":
        for m in e.get("messages", []):
            c[m.get("target")] += 1
print(c)
