"""Phase 2 (issue #148): capture a REAL browser session on /deviceMessages.

Opens the page in Chromium, records every WebSocket frame in both directions
(base64 JSONL, same shape as scripts/sniff_websocket.py), then checks all
"Show unsupported/internal values" checkboxes exactly like the user's
Playwright workaround and saves the fully rendered table.

The outgoing frames around the checkbox clicks are the ground truth for why
our synthetic DispatchEventAsync calls are rejected by the box.

Usage:
    python scripts/phase2_browser_capture.py [http://192.168.130.74]
"""
import asyncio
import base64
import datetime
import json
import sys

from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://192.168.130.74"
OUT_DIR = r"E:\Github\enpal\dist\poc\attachments\browser_capture"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


async def main() -> None:
    import os
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = rf"{OUT_DIR}\browser_ws_{stamp}.jsonl"
    log = open(jsonl_path, "w", encoding="utf-8")

    def record(entry: dict) -> None:
        entry["ts"] = _now()
        log.write(json.dumps(entry, ensure_ascii=False) + "\n")
        log.flush()

    def frame_payload(payload) -> dict:
        if isinstance(payload, bytes):
            return {"encoding": "base64", "data": base64.b64encode(payload).decode()}
        return {"encoding": "text", "data": payload}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()

        def on_ws(ws):
            record({"type": "ws_open", "url": ws.url})
            ws.on("framesent", lambda p: record({"type": "sent", **frame_payload(p)}))
            ws.on("framereceived", lambda p: record({"type": "recv", **frame_payload(p)}))
            ws.on("close", lambda w: record({"type": "ws_close"}))

        page.on("websocket", on_ws)

        print(f"opening {BASE}/deviceMessages ...")
        await page.goto(f"{BASE}/deviceMessages", wait_until="networkidle")
        await asyncio.sleep(5)  # let Blazor render the device tables

        html_before = await page.content()
        with open(rf"{OUT_DIR}\rendered_before_toggles_{stamp}.html", "w", encoding="utf-8") as f:
            f.write(html_before)
        rows_before = await page.locator("tbody tr").count()
        print(f"rows before toggles: {rows_before}")

        # Check every checkbox, one at a time, with a marker frame before each
        # click so the outgoing frames can be attributed in the JSONL.
        boxes = page.locator("input[type=checkbox]")
        count = await boxes.count()
        for i in range(count):
            box = boxes.nth(i)
            dom_id = await box.get_attribute("id")
            if not (dom_id or "").startswith(("showUnsupported_", "showInternal_")):
                continue
            if await box.is_checked():
                continue
            record({"type": "marker", "action": "click", "dom_id": dom_id})
            print(f"clicking {dom_id} ...")
            await box.check(timeout=5000, force=True)
            await asyncio.sleep(2)

        await asyncio.sleep(5)  # let the hidden rows render
        html_after = await page.content()
        with open(rf"{OUT_DIR}\rendered_after_toggles_{stamp}.html", "w", encoding="utf-8") as f:
            f.write(html_after)
        rows_after = await page.locator("tbody tr").count()
        print(f"rows after toggles: {rows_after}")

        await browser.close()

    log.close()
    print(f"WS log: {jsonl_path}")


if __name__ == "__main__":
    asyncio.run(main())
