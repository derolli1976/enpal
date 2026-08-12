"""Phase 2 (issue #148): test the browser click format from our own client.

The real-browser capture (scripts/phase2_browser_capture.py) showed the only
difference to our rejected clicks: the browser sends a populated
``eventFieldInfo`` while we sent ``null``, and the event args are
``{"value": true}`` without a ``"type"`` field::

    ["1", null, "DispatchEventAsync", 1,
     '[{"eventHandlerId":106,"eventName":"change",
        "eventFieldInfo":{"componentId":28,"fieldValue":true}},
       {"value":true}]']

This script reuses the sniffer, replaces the click payload with the browser
format and reports CLICK OK / CLICK FAILED per toggle.

Usage:
    python scripts/phase2_click_experiment.py [target] [--component-id 28] [--seconds 60]
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sniff_websocket as sw


def make_browser_format_click(component_id: int, field_info: bool, legacy_args: bool):
    async def _send_checkbox_change(self, dom_id: str, handler_id: int) -> None:
        self._dotnet_call_counter += 1
        call_id = self._dotnet_call_counter
        self._pending_toggle_calls[call_id] = dom_id
        self._last_toggle_sent = time.monotonic()

        event_descriptor = {
            "eventHandlerId": handler_id,
            "eventName": "change",
            "eventFieldInfo": (
                {"componentId": component_id, "fieldValue": True} if field_info else None
            ),
        }
        event_args = {"type": "change", "value": True} if legacy_args else {"value": True}
        args_json = json.dumps([event_descriptor, event_args])
        msg = [
            1, {}, None,
            "BeginInvokeDotNetFromJS",
            [str(call_id), None, "DispatchEventAsync", self._renderer_interop_id, args_json],
        ]
        await self._send(msg)
        sw._LOGGER.info(
            "CLICK sent (browser format): '%s' (handler %d, call %d, interop %d, componentId %d)",
            dom_id, handler_id, call_id, self._renderer_interop_id, component_id,
        )
        self._record({
            "type": "toggle_click",
            "dom_id": dom_id,
            "handler_id": handler_id,
            "call_id": call_id,
            "renderer_interop_id": self._renderer_interop_id,
            "component_id": component_id,
            "payload_format": "browser",
        })

    return _send_checkbox_change


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default="192.168.130.74")
    parser.add_argument("--component-id", type=int, default=28)
    parser.add_argument("--no-field-info", action="store_true")
    parser.add_argument("--legacy-args", action="store_true")
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--outdir", default=r"E:\Github\enpal\dist\poc\attachments\click_experiment")
    args = parser.parse_args()

    sw.EnpalSniffer._send_checkbox_change = make_browser_format_click(
        args.component_id, not args.no_field_info, args.legacy_args
    )

    sw.logging.basicConfig(level=sw.logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    sniffer = sw.EnpalSniffer(
        base_url=sw._normalize_base_url(args.target),
        outdir=Path(args.outdir),
        capture_html=True,
        click_toggles=True,
        toggle_delay=8.0,
    )
    try:
        await sniffer.connect()
        await sniffer.run(args.seconds)
    finally:
        try:
            await sniffer.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
