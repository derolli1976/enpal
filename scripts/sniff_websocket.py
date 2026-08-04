#!/usr/bin/env python3
"""
Enpal WebSocket Sniffer / Diagnostic Tool
=========================================

Listens to the Blazor SignalR WebSocket of an Enpal Box (/deviceMessages) for a
configurable amount of time and records EVERYTHING needed to understand how the
firmware (>= 8.50) pushes updates and "colours" freshly-updated sensors.

For every WebSocket frame it captures:
  * the raw binary frame (base64) and its decoded MessagePack messages
  * RenderBatch edit frames (the binary diff payload is stored base64-encoded so
    it can be reverse-engineered offline later)

On every RenderBatch it additionally HTTP-scrapes /deviceMessages and computes a
DIFF against the previous scrape, so you can correlate which sensor *values*
changed with each push - this is the key to understanding the new colouring /
incremental-update behaviour.

Output:
  * Console: human-readable live log (frames, message types, changed sensors)
  * File   : poc/ws_sniff_<timestamp>.jsonl   (one JSON object per event)
  * File   : poc/ws_sniff_<timestamp>_deviceMessages_<n>.html  (raw HTML snapshots)

Firmware 8.51: the sniffer answers Radzen/MudBlazor JS calls with the same
literals as the integration (otherwise the circuit dies) and can optionally
test the "Show unsupported/internal values" checkbox toggles that reveal
hidden rows such as the battery SOC (--click-toggles).

Usage:
    python scripts/sniff_websocket.py <enpal_box_ip_or_url> [--seconds 120]
                                      [--no-html] [--outdir poc]
                                      [--click-toggles] [--toggle-delay 10]

Examples:
    python scripts/sniff_websocket.py 192.168.1.50
    python scripts/sniff_websocket.py http://192.168.1.50 --seconds 300
    python scripts/sniff_websocket.py 192.168.1.50 --seconds 180 --click-toggles

Only depends on: aiohttp, msgpack, beautifulsoup4 (all already in requirements).
The Blazor protocol helpers are loaded directly from the integration's
api/protocol.py (it has no Home-Assistant dependencies).
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import importlib.util
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Load the Blazor protocol helpers from the integration (no HA dependencies).
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_API_DIR = _REPO_ROOT / "custom_components" / "enpal_webparser" / "api"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_protocol = _load_module("enpal_protocol", _API_DIR / "protocol.py")
encode_message = _protocol.encode_message
decode_messages = _protocol.decode_messages
extract_blazor_components = _protocol.extract_blazor_components
extract_application_state = _protocol.extract_application_state

_render_batch = _load_module("enpal_render_batch", _API_DIR / "render_batch.py")
extract_event_handlers = _render_batch.extract_event_handlers

# Mirrors websocket_client._JS_CALL_RESULTS: answering these with null crashes
# the circuit on firmware 8.51.
_JS_CALL_RESULTS = {
    "mudpopoverHelper.countProviders": "1",
    "Radzen.createChart": '{"left":0,"top":0,"width":800,"height":400}',
    "Radzen.createResizable": '{"left":0,"top":0,"width":800,"height":400}',
}

_TOGGLE_ID_PREFIXES = ("showUnsupported_", "showInternal_")


_LOGGER = logging.getLogger("enpal_sniffer")


# Map SignalR / Blazor message type ids to readable names for the console log.
_MSG_TYPE_NAMES = {
    1: "Invocation",
    2: "StreamItem",
    3: "Completion",
    4: "StreamInvocation",
    5: "CancelInvocation",
    6: "Ping",
    7: "Close",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_base_url(raw: str) -> str:
    raw = raw.strip().rstrip("/")
    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = "http://" + raw
    if raw.endswith("/deviceMessages"):
        raw = raw[: -len("/deviceMessages")]
    return raw


def _parse_sensor_table(html: str) -> Dict[str, Dict[str, Any]]:
    """Parse /deviceMessages into a flat {sensor_key: {...}} dict for diffing.

    Self-contained (does not depend on the integration's utils/const) so the
    sniffer keeps working even if the parsing logic changes.  Keys are
    ``"<Group> / <Sensor>"`` to stay unique across groups.
    """
    soup = BeautifulSoup(html, "html.parser")
    result: Dict[str, Dict[str, Any]] = {}

    for card in soup.find_all("div", class_="card"):
        header = card.find(["h1", "h2", "h3"])
        group = header.text.strip() if header else "Unknown"

        for row in card.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 2:
                continue
            name = cols[0].text.strip()
            value = cols[1].text.strip()
            timestamp = cols[2].text.strip() if len(cols) > 2 else None
            # Capture CSS classes/style on the row + value cell - the firmware
            # is reported to "colour" freshly-updated cells, so record any hint.
            row_classes = row.get("class") or []
            value_classes = cols[1].get("class") or []
            value_style = cols[1].get("style")
            key = f"{group} / {name}"
            result[key] = {
                "group": group,
                "name": name,
                "value": value,
                "timestamp": timestamp,
                "row_classes": list(row_classes),
                "value_classes": list(value_classes),
                "value_style": value_style,
            }

    return result


def _diff_snapshots(
    old: Dict[str, Dict[str, Any]],
    new: Dict[str, Dict[str, Any]],
) -> Dict[str, List[Any]]:
    """Compute added/removed/changed sensors between two snapshots."""
    old_keys = set(old)
    new_keys = set(new)

    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)

    changed = []
    for key in sorted(old_keys & new_keys):
        o = old[key]
        n = new[key]
        fields = {}
        for field in ("value", "timestamp", "row_classes", "value_classes", "value_style"):
            if o.get(field) != n.get(field):
                fields[field] = {"old": o.get(field), "new": n.get(field)}
        if fields:
            changed.append({"key": key, "fields": fields})

    return {"added": added, "removed": removed, "changed": changed}


class EnpalSniffer:
    def __init__(
        self,
        base_url: str,
        outdir: Path,
        capture_html: bool = True,
        click_toggles: bool = False,
        toggle_delay: float = 10.0,
    ):
        self.base_url = base_url
        self.outdir = outdir
        self.capture_html = capture_html
        self.click_toggles = click_toggles
        self.toggle_delay = toggle_delay

        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.components: List[Any] = []
        self.application_state: str = ""

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.outdir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.outdir / f"ws_sniff_{ts}.jsonl"
        self._html_prefix = f"ws_sniff_{ts}_deviceMessages"
        self._jsonl_file = self.jsonl_path.open("w", encoding="utf-8")

        self._frame_no = 0
        self._scrape_no = 0
        self._last_snapshot: Dict[str, Dict[str, Any]] = {}
        self._render_batch_count = 0
        self._start_time = time.monotonic()

        # Toggle-click test state (mirrors websocket_client).
        self._toggle_handlers: Dict[str, int] = {}
        self._toggles_attempted: Dict[str, int] = {}
        self._pending_toggle_calls: Dict[int, str] = {}
        self._renderer_interop_id = 1
        self._dotnet_call_counter = 0
        self._last_toggle_sent: Optional[float] = None

    # ------------------------------------------------------------------
    # Event recording
    # ------------------------------------------------------------------
    def _record(self, event: Dict[str, Any]) -> None:
        event["ts"] = _now_iso()
        event["elapsed"] = round(time.monotonic() - self._start_time, 3)
        self._jsonl_file.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._jsonl_file.flush()

    # ------------------------------------------------------------------
    # Connection setup (mirrors EnpalWebSocketClient.connect)
    # ------------------------------------------------------------------
    async def connect(self) -> None:
        self.session = aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar(),
            connector=aiohttp.TCPConnector(use_dns_cache=False),
        )

        _LOGGER.info("Loading %s/deviceMessages ...", self.base_url)
        async with self.session.get(f"{self.base_url}/deviceMessages") as resp:
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status} loading /deviceMessages")
            html = await resp.text()
            self.components = extract_blazor_components(html)
            self.application_state = extract_application_state(html)

        if not self.components:
            raise RuntimeError("No Blazor components found - is this an Enpal box >= 8.50?")
        if not self.application_state:
            raise RuntimeError("No Blazor application state found")

        _LOGGER.info("Found %d Blazor components", len(self.components))

        # Initial snapshot baseline + fixture dump.
        self._last_snapshot = _parse_sensor_table(html)
        self._dump_html(html, reason="initial")
        _LOGGER.info("Baseline snapshot: %d sensors", len(self._last_snapshot))

        async with self.session.post(
            f"{self.base_url}/_blazor/negotiate?negotiateVersion=1", data=""
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status} during negotiate")
            negotiate = await resp.json()
            token = negotiate.get("connectionToken")
            if not token:
                raise RuntimeError("No connectionToken in negotiate response")

        host = self.base_url.replace("http://", "").replace("https://", "")
        ws_url = f"ws://{host}/_blazor?id={token}"
        self.ws = await self.session.ws_connect(ws_url)

        # Blazor handshake.
        await self.ws.send_str('{"protocol":"blazorpack","version":1}\x1e')
        msg = await self.ws.receive()
        if msg.type == aiohttp.WSMsgType.TEXT:
            hs = msg.data.rstrip("\x1e")
        elif msg.type == aiohttp.WSMsgType.BINARY:
            hs = msg.data.decode("utf-8", "replace").rstrip("\x1e")
        else:
            raise RuntimeError(f"Unexpected handshake response: {msg.type}")
        if '"error"' in hs:
            raise RuntimeError(f"Handshake error: {hs}")
        _LOGGER.info("Handshake OK")

        await self._send_start_circuit()
        await asyncio.sleep(0.3)
        await self._send_update_root_components()
        await asyncio.sleep(0.5)
        _LOGGER.info("Circuit started - listening for RenderBatch pushes ...")

    # ------------------------------------------------------------------
    # Blazor outgoing messages
    # ------------------------------------------------------------------
    async def _send(self, msg: List[Any]) -> None:
        assert self.ws is not None
        await self.ws.send_bytes(encode_message(msg))

    async def _send_start_circuit(self) -> None:
        await self._send([
            1, {}, "0", "StartCircuit",
            [
                self.base_url + "/",
                self.base_url + "/deviceMessages",
                "[]",
                self.application_state,
            ],
        ])

    async def _send_update_root_components(self) -> None:
        operations = [
            {
                "type": "add",
                "ssrComponentId": i + 1,
                "marker": {
                    "type": comp.type,
                    "prerenderId": comp.prerender_id,
                    "key": comp.key,
                    "sequence": comp.sequence,
                    "descriptor": comp.descriptor,
                    "uniqueId": i,
                },
            }
            for i, comp in enumerate(self.components)
        ]
        batch_json = json.dumps({"batchId": 1, "operations": operations})
        await self._send([1, {}, None, "UpdateRootComponents", [batch_json, self.application_state]])

    async def _send_on_render_completed(self, batch_id: int) -> None:
        await self._send([1, {}, None, "OnRenderCompleted", [batch_id, None]])

    async def _send_end_invoke_js(self, task_id: int, result: str = "null") -> None:
        result_json = f"[{task_id},true,{result}]"
        await self._send([1, {}, None, "EndInvokeJSFromDotNet", [task_id, True, result_json]])

    async def _send_ping(self) -> None:
        await self._send([6])

    # ------------------------------------------------------------------
    # Receive loop
    # ------------------------------------------------------------------
    async def run(self, seconds: float) -> None:
        assert self.ws is not None
        deadline = time.monotonic() + seconds
        ping_at = time.monotonic() + 15

        while time.monotonic() < deadline:
            timeout = max(0.1, min(deadline, ping_at) - time.monotonic())
            try:
                msg = await asyncio.wait_for(self.ws.receive(), timeout=timeout)
            except asyncio.TimeoutError:
                if time.monotonic() >= ping_at:
                    await self._send_ping()
                    ping_at = time.monotonic() + 15
                continue

            if msg.type == aiohttp.WSMsgType.BINARY:
                await self._handle_binary(msg.data)
            elif msg.type == aiohttp.WSMsgType.TEXT:
                self._record({"type": "ws_text", "data": msg.data})
                _LOGGER.debug("TEXT frame: %s", msg.data)
            elif msg.type in (
                aiohttp.WSMsgType.CLOSED,
                aiohttp.WSMsgType.CLOSING,
                aiohttp.WSMsgType.ERROR,
            ):
                _LOGGER.warning("WebSocket closed (type=%s)", msg.type)
                self._record({"type": "ws_closed", "ws_type": str(msg.type)})
                break

        _LOGGER.info(
            "Done. %d frames, %d RenderBatches, %d scrapes captured.",
            self._frame_no, self._render_batch_count, self._scrape_no,
        )

    async def _handle_binary(self, data: bytes) -> None:
        self._frame_no += 1
        frame_no = self._frame_no

        # Always store the raw frame so the binary RenderBatch diff format can
        # be reverse-engineered offline later.
        raw_b64 = base64.b64encode(data).decode("ascii")

        try:
            messages = decode_messages(data)
        except Exception as exc:  # noqa: BLE001 - diagnostic tool, keep going
            self._record({
                "type": "ws_binary",
                "frame": frame_no,
                "bytes": len(data),
                "raw_b64": raw_b64,
                "decode_error": str(exc),
            })
            _LOGGER.warning("Frame #%d: decode error %s", frame_no, exc)
            return

        decoded_summary = []
        has_render_batch = False

        for msg in messages:
            if not isinstance(msg, list) or not msg:
                continue
            msg_type = msg[0]
            type_name = _MSG_TYPE_NAMES.get(msg_type, f"Type{msg_type}")

            entry: Dict[str, Any] = {"msg_type": msg_type, "type_name": type_name}

            if msg_type == 1 and len(msg) >= 4:
                target = msg[3]
                args = msg[4] if len(msg) > 4 else []
                entry["target"] = target
                entry["arg_summary"] = _summarize_args(target, args)

                if target == "JS.RenderBatch":
                    has_render_batch = True
                    if args:
                        # args[0] is the binary diff payload; keep it raw.
                        batch_id = args[0] if isinstance(args[0], int) else None
                        payload = args[1] if len(args) > 1 else None
                        if isinstance(payload, (bytes, bytearray)):
                            entry["render_batch_payload_b64"] = base64.b64encode(
                                bytes(payload)
                            ).decode("ascii")
                            entry["render_batch_payload_bytes"] = len(payload)
                            if self.click_toggles:
                                self._collect_toggle_handlers(bytes(payload))
                        entry["render_batch_id"] = batch_id
                        try:
                            await self._send_on_render_completed(args[0])
                        except Exception:  # noqa: BLE001
                            pass
                elif target == "JS.BeginInvokeJS":
                    if args:
                        identifier = args[1] if len(args) > 1 else ""
                        if len(args) > 2 and isinstance(args[2], str):
                            self._try_capture_renderer_interop_id(args[2])
                        try:
                            await self._send_end_invoke_js(
                                args[0], _JS_CALL_RESULTS.get(identifier, "null")
                            )
                        except Exception:  # noqa: BLE001
                            pass
                elif target == "JS.EndInvokeDotNet":
                    self._handle_end_invoke_dotnet(args, entry)
                elif target == "JS.Error":
                    _LOGGER.warning("JS.Error from box: %s", args[0] if args else None)
                    self._log_toggle_blame("JS.Error")

            elif msg_type == 3:
                entry["completion"] = _stringify(msg[1:])
            elif msg_type == 7:
                close_error = _stringify(msg[1] if len(msg) > 1 else None)
                entry["close_error"] = close_error
                _LOGGER.warning("Close message from box: %s", close_error)
                self._log_toggle_blame("Close")

            decoded_summary.append(entry)

        self._record({
            "type": "ws_binary",
            "frame": frame_no,
            "bytes": len(data),
            "raw_b64": raw_b64,
            "messages": decoded_summary,
        })

        targets = [e.get("target") for e in decoded_summary if e.get("target")]
        types = [e["type_name"] for e in decoded_summary]
        _LOGGER.info("Frame #%d (%d bytes): %s%s",
                     frame_no, len(data),
                     ", ".join(types),
                     f"  targets={targets}" if targets else "")

        if has_render_batch:
            self._render_batch_count += 1
            await self._scrape_and_diff()
            if self.click_toggles:
                await self._activate_next_toggle()

    # ------------------------------------------------------------------
    # Page-toggle click test (mirrors websocket_client)
    # ------------------------------------------------------------------
    def _collect_toggle_handlers(self, batch_bytes: bytes) -> None:
        try:
            handlers = extract_event_handlers(batch_bytes)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("extract_event_handlers failed: %s", exc)
            return
        for dom_id, handler_id in handlers.items():
            if not dom_id.startswith(_TOGGLE_ID_PREFIXES):
                continue
            if self._toggle_handlers.get(dom_id) != handler_id:
                _LOGGER.info("Toggle handler found: %s -> event handler %d", dom_id, handler_id)
                self._record({"type": "toggle_handler", "dom_id": dom_id, "handler_id": handler_id})
            self._toggle_handlers[dom_id] = handler_id

    async def _activate_next_toggle(self) -> None:
        if self.ws is None or self.ws.closed:
            return
        if time.monotonic() - self._start_time < self.toggle_delay:
            return
        for dom_id, handler_id in self._toggle_handlers.items():
            if self._toggles_attempted.get(dom_id) == handler_id:
                continue
            self._toggles_attempted[dom_id] = handler_id
            await self._send_checkbox_change(dom_id, handler_id)
            return

    async def _send_checkbox_change(self, dom_id: str, handler_id: int) -> None:
        self._dotnet_call_counter += 1
        call_id = self._dotnet_call_counter
        self._pending_toggle_calls[call_id] = dom_id
        self._last_toggle_sent = time.monotonic()

        event_descriptor = {
            "eventHandlerId": handler_id,
            "eventName": "change",
            "eventFieldInfo": None,
        }
        event_args = {"type": "change", "value": True}
        args_json = json.dumps([event_descriptor, event_args])
        msg = [
            1, {}, None,
            "BeginInvokeDotNetFromJS",
            [str(call_id), None, "DispatchEventAsync", self._renderer_interop_id, args_json],
        ]
        await self._send(msg)
        _LOGGER.info(
            "CLICK sent: '%s' (handler %d, call %d, interop %d)",
            dom_id, handler_id, call_id, self._renderer_interop_id,
        )
        self._record({
            "type": "toggle_click",
            "dom_id": dom_id,
            "handler_id": handler_id,
            "call_id": call_id,
            "renderer_interop_id": self._renderer_interop_id,
        })

    def _handle_end_invoke_dotnet(self, args: Any, entry: Dict[str, Any]) -> None:
        call_id = args[0] if args else None
        success = args[1] if len(args) > 1 else False
        try:
            call_id_int = int(call_id)
        except (TypeError, ValueError):
            call_id_int = None
        dom_id = self._pending_toggle_calls.pop(call_id_int, None)
        entry["toggle_dom_id"] = dom_id
        entry["toggle_success"] = bool(success)
        if dom_id is None:
            return
        if success:
            _LOGGER.info("CLICK OK: toggle '%s' accepted by the box", dom_id)
        else:
            _LOGGER.warning(
                "CLICK FAILED: toggle '%s' rejected: %s",
                dom_id, args[2] if len(args) > 2 else None,
            )

    def _try_capture_renderer_interop_id(self, args_json_str: str) -> None:
        if '"__dotNetObject"' not in args_json_str:
            return
        try:
            parsed = json.loads(args_json_str)
        except (json.JSONDecodeError, TypeError):
            return
        if not isinstance(parsed, list):
            return
        for item in parsed:
            if isinstance(item, dict) and isinstance(item.get("__dotNetObject"), int):
                obj_id = item["__dotNetObject"]
                if obj_id > 0:
                    self._renderer_interop_id = obj_id
                    _LOGGER.info("Renderer DotNet object ref captured: %d", obj_id)
                    return

    def _log_toggle_blame(self, reason: str) -> None:
        if not self._last_toggle_sent:
            return
        elapsed = time.monotonic() - self._last_toggle_sent
        _LOGGER.warning(
            "%s arrived %.1fs after the last toggle click - the click likely killed the circuit",
            reason, elapsed,
        )
        self._record({"type": "toggle_blame", "reason": reason, "seconds_after_click": round(elapsed, 3)})

    # ------------------------------------------------------------------
    # HTTP scrape + diff
    # ------------------------------------------------------------------
    async def _scrape_and_diff(self) -> None:
        assert self.session is not None
        try:
            async with self.session.get(
                f"{self.base_url}/deviceMessages",
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Scrape failed: HTTP %d", resp.status)
                    return
                html = await resp.text()
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Scrape error: %s", exc)
            return

        self._scrape_no += 1
        snapshot = _parse_sensor_table(html)
        diff = _diff_snapshots(self._last_snapshot, snapshot)
        self._last_snapshot = snapshot

        if self.capture_html and (diff["added"] or diff["removed"] or diff["changed"]):
            self._dump_html(html, reason=f"scrape{self._scrape_no}")

        self._record({
            "type": "scrape_diff",
            "scrape": self._scrape_no,
            "render_batch": self._render_batch_count,
            "sensor_count": len(snapshot),
            "diff": diff,
        })

        n_changed = len(diff["changed"])
        if diff["added"] or diff["removed"] or n_changed:
            _LOGGER.info(
                "  -> scrape #%d: %d changed, %d added, %d removed",
                self._scrape_no, n_changed, len(diff["added"]), len(diff["removed"]),
            )
            for ch in diff["changed"][:25]:
                fields = ch["fields"]
                if "value" in fields:
                    _LOGGER.info(
                        "       %s: %s -> %s",
                        ch["key"], fields["value"]["old"], fields["value"]["new"],
                    )
                else:
                    _LOGGER.info("       %s: %s", ch["key"], list(fields.keys()))
            for key in diff["added"]:
                _LOGGER.info("       + ADDED  %s = %s", key, snapshot[key]["value"])
            for key in diff["removed"]:
                _LOGGER.info("       - REMOVED %s", key)
        else:
            _LOGGER.info("  -> scrape #%d: no sensor changes", self._scrape_no)

    def _dump_html(self, html: str, reason: str) -> None:
        if not self.capture_html:
            return
        path = self.outdir / f"{self._html_prefix}_{reason}.html"
        try:
            path.write_text(html, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Could not write HTML snapshot: %s", exc)

    # ------------------------------------------------------------------
    async def close(self) -> None:
        if self.ws and not self.ws.closed:
            try:
                await self.ws.close()
            except Exception:  # noqa: BLE001
                pass
        if self.session and not self.session.closed:
            try:
                await self.session.close()
            except Exception:  # noqa: BLE001
                pass
        self._jsonl_file.close()
        _LOGGER.info("Log written to: %s", self.jsonl_path)


def _summarize_args(target: Optional[str], args: Any) -> Any:
    """Make invocation args JSON-serialisable and reasonably compact."""
    try:
        return _stringify(args, max_len=400)
    except Exception:  # noqa: BLE001
        return repr(args)[:400]


def _stringify(obj: Any, max_len: int = 2000) -> Any:
    """Recursively convert bytes to base64 and truncate long strings."""
    if isinstance(obj, (bytes, bytearray)):
        b64 = base64.b64encode(bytes(obj)).decode("ascii")
        return {"__bytes_b64__": b64, "len": len(obj)}
    if isinstance(obj, str):
        return obj if len(obj) <= max_len else obj[:max_len] + f"...(+{len(obj) - max_len})"
    if isinstance(obj, list):
        return [_stringify(x, max_len) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _stringify(v, max_len) for k, v in obj.items()}
    return obj


async def _main_async(args: argparse.Namespace) -> int:
    base_url = _normalize_base_url(args.target)
    outdir = Path(args.outdir)
    if not outdir.is_absolute():
        outdir = _REPO_ROOT / outdir

    sniffer = EnpalSniffer(
        base_url,
        outdir,
        capture_html=not args.no_html,
        click_toggles=args.click_toggles,
        toggle_delay=args.toggle_delay,
    )
    try:
        await sniffer.connect()
        await sniffer.run(args.seconds)
    except KeyboardInterrupt:
        _LOGGER.info("Interrupted by user")
    except Exception as exc:  # noqa: BLE001
        _LOGGER.error("Sniffer failed: %s", exc, exc_info=True)
        return 1
    finally:
        await sniffer.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sniff the Enpal Box Blazor WebSocket and record sensor updates.",
    )
    parser.add_argument("target", help="Enpal box IP or URL (e.g. 192.168.1.50)")
    parser.add_argument("--seconds", type=float, default=120,
                        help="How long to listen (default: 120)")
    parser.add_argument("--outdir", default="poc",
                        help="Output directory (default: poc)")
    parser.add_argument("--no-html", action="store_true",
                        help="Do not save HTML snapshots")
    parser.add_argument("--click-toggles", action="store_true",
                        help="Click the 'Show unsupported/internal values' checkboxes "
                             "after --toggle-delay seconds and record the outcome")
    parser.add_argument("--toggle-delay", type=float, default=10,
                        help="Seconds to wait before the first toggle click (default: 10)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
