"""Dump all JS.BeginInvokeJS calls with their arg summaries (which __dotNetObject refs exist?)."""
import json, sys

p = sys.argv[1]
for line in open(p, encoding="utf-8"):
    e = json.loads(line)
    if e["type"] != "ws_binary":
        continue
    for m in e.get("messages", []):
        if m.get("target") == "JS.BeginInvokeJS":
            print(f"[{e['elapsed']:>8}] BeginInvokeJS: {json.dumps(m.get('arg_summary'))[:500]}")
        if m.get("target") == "JS.AttachComponent":
            print(f"[{e['elapsed']:>8}] AttachComponent: {json.dumps(m.get('arg_summary'))[:200]}")
