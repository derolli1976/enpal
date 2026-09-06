"""Phase 0 (InfluxDB data source): read-only schema snapshot of the Enpal box InfluxDB.

Collects everything needed to design the Influx client:
  * /health  -> version (InfluxDB 1.x vs 2.x)
  * /api/v2/buckets -> bucket names
  * per bucket: measurements, field keys, tag keys (Flux schema functions)
  * per bucket: last value per series (raw annotated CSV saved as fixture)
  * comparison of measurement/field names against SENSOR_KEY_GROUPS

The access token is NOT passed on the command line (shell history!). Set it as
an environment variable before running:

    $env:ENPAL_INFLUX_TOKEN = "<token>"
    $env:ENPAL_INFLUX_ORG   = "<organisation>"
    python scripts/influx_snapshot.py [http://192.168.2.70] [--outdir dist/poc/influx]

Only stdlib is used (urllib), no new dependencies.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from custom_components.enpal_webparser.const import (  # noqa: E402
    SENSOR_KEY_ALIASES,
    SENSOR_KEY_GROUPS,
)

TIMEOUT = 15


def _request(url: str, token: str | None = None, data: bytes | None = None,
             content_type: str | None = None) -> tuple[int, str]:
    headers = {"User-Agent": "enpal-influx-snapshot"}
    if token:
        headers["Authorization"] = f"Token {token}"
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def flux(base: str, org: str, token: str, query: str) -> tuple[int, str]:
    url = f"{base}/api/v2/query?org={urllib.parse.quote(org)}"
    return _request(url, token, query.encode("utf-8"),
                    "application/vnd.flux")


def csv_column(body: str, column: str) -> list[str]:
    """Extract one column from annotated Flux CSV (skips annotation lines)."""
    values: list[str] = []
    for table in body.split("\r\n\r\n"):
        lines = [ln for ln in table.splitlines() if ln and not ln.startswith("#")]
        if not lines:
            continue
        reader = csv.DictReader(lines)
        for row in reader:
            v = (row.get(column) or "").strip()
            if v:
                values.append(v)
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base", nargs="?", default="http://192.168.2.70")
    parser.add_argument("--port", type=int, default=8086)
    parser.add_argument("--outdir", default=str(REPO / "dist" / "poc" / "influx"))
    parser.add_argument("--range", default="-2h", help="Flux range start for last-value query")
    args = parser.parse_args()

    token = os.environ.get("ENPAL_INFLUX_TOKEN", "")
    org = os.environ.get("ENPAL_INFLUX_ORG", "")
    # Fallback: dist/influx_credentials.json {"token": "...", "org": "..."}
    # (dist/ is gitignored; avoids per-terminal-session env var issues)
    cred_file = REPO / "dist" / "influx_credentials.json"
    if (not token or not org) and cred_file.exists():
        creds = json.loads(cred_file.read_text(encoding="utf-8"))
        token = token or creds.get("token", "")
        org = org or creds.get("org", "")
        print(f"credentials loaded from {cred_file}")

    host = args.base.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0]
    base = f"http://{host}:{args.port}"
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    summary: dict = {"base": base, "timestamp": stamp}

    # 1. Health / version (no auth required)
    status, body = _request(f"{base}/health")
    print(f"/health -> HTTP {status}")
    print(body[:300])
    summary["health"] = {"status": status, "body": body[:500]}
    if status != 200:
        print("InfluxDB not reachable, aborting.")
        _write(outdir, stamp, summary)
        return

    if not token or not org:
        print("\nENPAL_INFLUX_TOKEN / ENPAL_INFLUX_ORG not set - stopping after health check.")
        print("Set both environment variables and re-run for the full snapshot.")
        _write(outdir, stamp, summary)
        return

    # 2. Buckets
    status, body = _request(f"{base}/api/v2/buckets?limit=100", token)
    print(f"\n/api/v2/buckets -> HTTP {status}")
    if status != 200:
        print(body[:500])
        summary["buckets_error"] = {"status": status, "body": body[:500]}
        _write(outdir, stamp, summary)
        return
    buckets_json = json.loads(body)
    buckets = [b["name"] for b in buckets_json.get("buckets", [])]
    user_buckets = [b for b in buckets if not b.startswith("_")]
    print("buckets:", buckets)
    summary["buckets"] = buckets

    known_keys = set(SENSOR_KEY_GROUPS) | set(SENSOR_KEY_ALIASES)
    summary["bucket_details"] = {}

    for bucket in user_buckets:
        detail: dict = {}
        print(f"\n=== bucket {bucket!r} ===")

        status, body = flux(base, org, token,
                            f'import "influxdata/influxdb/schema"\n'
                            f'schema.measurements(bucket: "{bucket}")')
        measurements = csv_column(body, "_value") if status == 200 else []
        print(f"measurements ({len(measurements)}):", measurements[:40])
        detail["measurements"] = measurements

        status, body = flux(base, org, token,
                            f'import "influxdata/influxdb/schema"\n'
                            f'schema.fieldKeys(bucket: "{bucket}")')
        fields = csv_column(body, "_value") if status == 200 else []
        print(f"field keys ({len(fields)}):", fields[:40])
        detail["field_keys"] = fields

        status, body = flux(base, org, token,
                            f'import "influxdata/influxdb/schema"\n'
                            f'schema.tagKeys(bucket: "{bucket}")')
        tags = csv_column(body, "_value") if status == 200 else []
        print(f"tag keys ({len(tags)}):", tags)
        detail["tag_keys"] = tags

        # Last value per series - the raw CSV doubles as a parser fixture.
        status, body = flux(base, org, token,
                            f'from(bucket: "{bucket}") '
                            f'|> range(start: {args.range}) '
                            f'|> last()')
        print(f"last-value query -> HTTP {status}, {len(body)} chars")
        if status == 200:
            fixture = outdir / f"last_values_{bucket}_{stamp}.csv"
            fixture.write_text(body, encoding="utf-8")
            print(f"raw CSV saved to {fixture}")
            detail["last_values_csv"] = fixture.name
            series = csv_column(body, "_measurement")
            detail["series_count"] = len(series)
            # Key comparison: measurement and field names vs. SENSOR_KEY_GROUPS
            candidates = set(measurements) | set(fields) | set(series)
            matches = sorted(c for c in candidates if c in known_keys)
            misses = sorted(c for c in candidates if c not in known_keys)
            print(f"series: {len(series)}, dotted-key matches: {len(matches)}, "
                  f"unknown names: {len(misses)}")
            print("matches sample:", matches[:20])
            print("unknown sample:", misses[:40])
            detail["key_matches"] = matches
            detail["key_misses"] = misses
        else:
            print(body[:500])
            detail["last_values_error"] = body[:500]

        summary["bucket_details"][bucket] = detail

    _write(outdir, stamp, summary)


def _write(outdir: Path, stamp: str, summary: dict) -> None:
    out = outdir / f"influx_snapshot_{stamp}.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsummary written to {out}")


if __name__ == "__main__":
    main()
