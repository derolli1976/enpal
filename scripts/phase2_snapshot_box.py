"""Phase 2 (issue #148): snapshot the live box state over VPN.

Read-only: saves the initial HTML of /deviceMessages and prints the page
structure (groups, device spans, checkbox ids, pre-rendered rows).

Usage:
    python scripts/phase2_snapshot_box.py [http://192.168.130.74]
"""
import re
import sys
import datetime
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://192.168.130.74"
OUT_DIR = r"E:\Github\enpal\dist\poc\attachments"


def main() -> None:
    req = urllib.request.Request(
        f"{BASE}/deviceMessages", headers={"User-Agent": "enpal-debug"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        html = r.read().decode("utf-8", errors="replace")

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = rf"{OUT_DIR}\live_box_deviceMessages_{stamp}.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"saved {len(html)} chars to {out}")

    print("H2 groups:", re.findall(r"<h2[^>]*>(.*?)</h2>", html))
    print("device spans:", re.findall(r"</h2>\s*<span>([^<]+)</span>", html))
    print("checkbox ids:", re.findall(r'id="(show[A-Za-z_]+)"', html))
    rows = re.findall(r"<td>([A-Za-z0-9.]+)</td>\s*<td>([^<]*)</td>", html)
    print(f"pre-rendered rows ({len(rows)}):")
    for key, value in rows:
        print(f"  {key} = {value}")


if __name__ == "__main__":
    main()
