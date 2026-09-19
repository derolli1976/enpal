"""Issue #187: measure how often the Enpal box actually writes to its InfluxDB.

Two read-only Flux queries against the box:
  A) point count per series over a window -> average write interval per field
  B) raw points for the fields named in issue #187 -> interval distribution and
     how often the VALUE actually changes (vs. identical points being rewritten)

Credentials come from dist/influx_credentials.json ({"token": ..., "org": ...})
or ENPAL_INFLUX_TOKEN / ENPAL_INFLUX_ORG.

    python scripts/influx_update_rate.py [http://192.168.2.70] [--window 2h] [--detail 30m]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

TIMEOUT = 60

# Fields named in issue #187 (entity id -> dotted Influx field key).
DETAIL_FIELDS = [
    "Power.Consumption.Total",
    "Power.Consumption.AC",
    "Power.Production.Total",
    "Power.DC.Total",
    "Power.Grid.Export",
    "Power.External.Total",
    "Power.Battery.Charge.Discharge",
    "Energy.Battery.Charge.Level",
    "Energy.Consumption.Total.Day",
    "Energy.Consumption.Total.Lifetime",
    "Energy.Production.Total.Day",
    "Energy.Production.Total.Lifetime",
    "Energy.Grid.Export.Day",
    "Energy.Grid.Export.Lifetime",
    "Energy.Grid.Import.Day",
    "Energy.Grid.Import.Lifetime",
    "Energy.Battery.Charge.Day",
    "Energy.Battery.Discharge.Day",
    "Energy.Battery.Charge.Lifetime",
    "Energy.Battery.Discharge.Lifetime",
]


def flux(base: str, org: str, token: str, query: str) -> str:
    url = f"{base}/api/v2/query?org={urllib.parse.quote(org)}"
    req = urllib.request.Request(
        url,
        data=query.encode("utf-8"),
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/vnd.flux",
            "Accept": "application/csv",
            "User-Agent": "enpal-influx-update-rate",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Flux query failed: HTTP {e.code}\n{body[:500]}")


def parse_csv(body: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for line in body.splitlines():
        line = line.strip("\r")
        if not line.strip() or line.startswith("#"):
            continue
        cells = next(csv.reader(io.StringIO(line)))
        if cells[1:2] == ["result"] or "_field" in cells:
            header = cells
            continue
        if header:
            rows.append(dict(zip(header, cells)))
    return rows


def parse_time(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def fmt(seconds: float) -> str:
    return f"{seconds:7.1f}s"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", nargs="?", default="http://192.168.2.70")
    ap.add_argument("--port", type=int, default=8086)
    ap.add_argument("--window", default="2h", help="window for the per-series count query")
    ap.add_argument("--detail", default="30m", help="window for the raw-point query")
    args = ap.parse_args()

    token = os.environ.get("ENPAL_INFLUX_TOKEN", "")
    org = os.environ.get("ENPAL_INFLUX_ORG", "")
    cred = REPO / "dist" / "influx_credentials.json"
    if (not token or not org) and cred.exists():
        creds = json.loads(cred.read_text(encoding="utf-8"))
        token = token or creds.get("token", "")
        org = org or creds.get("org", "")
    if not token or not org:
        raise SystemExit("no InfluxDB credentials found")

    host = args.base.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0]
    base = f"http://{host}:{args.port}"

    window_s = {"m": 60, "h": 3600, "d": 86400}[args.window[-1]] * int(args.window[:-1])

    # --- A) point count per series -------------------------------------
    q_count = (
        'from(bucket: "solar")\n'
        f"  |> range(start: -{args.window})\n"
        '  |> filter(fn: (r) => r._field != "measureId")\n'
        '  |> group(columns: ["_measurement", "_field"])\n'
        "  |> count()\n"
    )
    counts = parse_csv(flux(base, org, token, q_count))
    per_series: list[tuple[str, str, int]] = []
    for row in counts:
        try:
            n = int(row.get("_value", "0"))
        except ValueError:
            continue
        per_series.append((row.get("_measurement", "?"), row.get("_field", "?"), n))

    print(f"=== A) write frequency per series, window -{args.window} ({window_s}s) ===")
    print(f"{len(per_series)} series\n")
    buckets: dict[str, int] = defaultdict(int)
    for _m, _f, n in per_series:
        if n == 0:
            buckets["no data"] += 1
            continue
        iv = window_s / n
        label = (
            "<= 5s" if iv <= 5.5 else
            "~10s" if iv <= 12 else
            "~15s" if iv <= 17 else
            "~30s" if iv <= 35 else
            "~60s" if iv <= 70 else
            "> 60s"
        )
        buckets[label] += 1
    for label in ("<= 5s", "~10s", "~15s", "~30s", "~60s", "> 60s", "no data"):
        if buckets.get(label):
            print(f"  avg write interval {label:>8}: {buckets[label]:4d} series")

    print("\n  detail fields:")
    by_field = {(m, f): n for m, f, n in per_series}
    for (m, f), n in sorted(by_field.items(), key=lambda kv: kv[0][1]):
        if f in DETAIL_FIELDS:
            iv = window_s / n if n else float("inf")
            print(f"    {m:>12}.{f:<36} {n:5d} points  avg {fmt(iv)}")

    # --- B) raw points for the issue fields ----------------------------
    field_set = ", ".join(f'"{f}"' for f in DETAIL_FIELDS)
    q_raw = (
        'from(bucket: "solar")\n'
        f"  |> range(start: -{args.detail})\n"
        f"  |> filter(fn: (r) => contains(value: r._field, set: [{field_set}]))\n"
        '  |> keep(columns: ["_time", "_value", "_measurement", "_field"])\n'
        '  |> group(columns: ["_measurement", "_field"])\n'
        '  |> sort(columns: ["_time"])\n'
    )
    raw = parse_csv(flux(base, org, token, q_raw))
    series: dict[tuple[str, str], list[tuple[dt.datetime, str]]] = defaultdict(list)
    for row in raw:
        t = row.get("_time")
        if not t:
            continue
        series[(row.get("_measurement", "?"), row.get("_field", "?"))].append(
            (parse_time(t), row.get("_value", ""))
        )

    print(f"\n=== B) raw points, window -{args.detail} ===")
    print(
        f"{'measurement.field':<52}{'pts':>5}{'min':>9}{'med':>9}{'max':>9}"
        f"{'changes':>9}{'med chg':>10}"
    )
    for key in sorted(series, key=lambda k: (k[1], k[0])):
        points = sorted(series[key])
        if len(points) < 2:
            print(f"{key[0]}.{key[1]:<40}{len(points):>5}  (too few points)")
            continue
        deltas = [
            (b[0] - a[0]).total_seconds() for a, b in zip(points, points[1:])
        ]
        change_times = [points[0][0]]
        last = points[0][1]
        for t, v in points[1:]:
            if v != last:
                change_times.append(t)
                last = v
        chg_deltas = [
            (b - a).total_seconds() for a, b in zip(change_times, change_times[1:])
        ]
        med_chg = statistics.median(chg_deltas) if chg_deltas else float("nan")
        name = f"{key[0]}.{key[1]}"
        print(
            f"{name:<52}{len(points):>5}{min(deltas):>8.1f}s"
            f"{statistics.median(deltas):>8.1f}s{max(deltas):>8.1f}s"
            f"{len(change_times) - 1:>9}{med_chg:>9.1f}s"
        )


if __name__ == "__main__":
    main()
