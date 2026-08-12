"""Incremental parser for Blazor RenderBatch binary diffs.

Instead of HTTP re-scraping ``/deviceMessages`` on every server push (which
forces the Enpal box to re-render the whole 130+ sensor page roughly every
five seconds), this module extracts only the *changed* sensor rows directly
from the RenderBatch binary payload that the box already sends us.

Binary layout (Blazor ``RenderBatchWriter``)
--------------------------------------------
The last 20 bytes of a RenderBatch are five little-endian ``int32`` section
offsets.  The final one points at the string table, which is an array of
``int32`` offsets, each pointing at a VLQ-length-prefixed UTF-8 string.

For the Enpal ``/deviceMessages`` page every updated table row is emitted, in
DOM order, as one of the following runs of strings::

    # firmware 8.50
    'dp-flash', '<Key>', '<ws>', '<value>'[, '<unit>'], '<ws>', '<timestamp>'

    # firmware 8.51 (extra Notes column, css helper classes)
    'dp-flash[ pi-row-validation]', '<Key>', '<value>'[, '<unit>'],
    'text-nowrap', ['style',] 'width: 1%;', '<timestamp>',
    'pi-note-cell', 'pi-note-text', '0', '<note text>'

    # firmware 8.51, row without a reading (note only)
    'dp-flash pi-row-validation', '<Key>', ['colspan',] '3', 'pi-note-cell', ...

where ``<ws>`` is a pure-whitespace separator.  Recovering the changed rows is
therefore a simple linear scan over the decoded string table - no virtual DOM
reconstruction required.

This is a best-effort fast path.  Anything it cannot resolve (ambiguous keys,
brand-new sensors, malformed frames) is left to the periodic full HTML scrape
the coordinator already performs, so the worst case degrades gracefully to
plain interval polling.
"""

import io
import re
import struct
import logging
from typing import Dict, List, Optional

_LOGGER = logging.getLogger(__name__)

# Strings that frame a sensor row but carry no data themselves.
_STRUCTURAL = {"onchange", "tr", "td", "class", "dp-flash", ""}

# 8.51: end of the value cell / start of a note-only row.
_VALUE_END = {"text-nowrap"}
_NOTE_MARKERS = {"pi-note-cell", "colspan"}

# 8.51 timestamps are time-only ("18:19:44.00"), 8.50 ones are full
# date-times; both contain an HH:MM:SS run.
_TIME_RE = re.compile(r"\d{1,2}:\d{2}:\d{2}")

# Sensor keys are dotted CamelCase identifiers ("Energy.Battery.Charge.Level",
# "LTE.RSSI"). The uppercase first segment keeps version strings ("v6.3") and
# numeric fragments ("226.3") out; non-row strings that happen to match (e.g.
# the assembly name) fail the value-termination check in _parse_row_body.
_KEY_RE = re.compile(r"^[A-Z][A-Za-z0-9]*(\.[A-Za-z0-9]+)+$")

_MAX_VALUE_TOKENS = 4

# Values longer than this are not sensor readings we want to patch
# incrementally (e.g. the inverter system-state bitfield, which the HTML
# parser splits into several sensors). Leave those to the full scrape.
_MAX_VALUE_LEN = 200


def _read_vlq(reader: io.BytesIO) -> int:
    """Decode a 7-bit variable-length quantity."""
    result = 0
    shift = 0
    while True:
        b = reader.read(1)
        if not b:
            raise EOFError()
        byte = b[0]
        result |= (byte & 0x7F) << shift
        if byte & 0x80 == 0:
            break
        shift += 7
    return result


def parse_render_batch_strings(raw: bytes) -> List[str]:
    """Decode the Blazor RenderBatch string table to an ordered list of strings.

    Returns an empty list if the buffer is too small or malformed - callers
    should treat that as "no incremental data" and rely on the full scrape.
    """
    if not raw or len(raw) < 20:
        return []
    try:
        string_table_offset = struct.unpack_from("<i", raw, len(raw) - 4)[0]
        if string_table_offset < 0 or string_table_offset > len(raw) - 20:
            return []

        table_region = raw[string_table_offset:len(raw) - 20]
        count = len(table_region) // 4
        if count <= 0:
            return []
        offsets = struct.unpack_from("<%di" % count, table_region, 0)

        strings: List[str] = []
        for off in offsets:
            if off < 0 or off >= len(raw):
                strings.append("")
                continue
            reader = io.BytesIO(raw[off:])
            length = _read_vlq(reader)
            strings.append(reader.read(length).decode("utf-8", "replace"))
        return strings
    except Exception as e:  # noqa: BLE001 - never let a bad frame break the loop
        _LOGGER.debug("[Enpal RenderBatch] string-table decode failed: %s", e)
        return []


def _is_ws(s: str) -> bool:
    return s.strip() == ""


def _is_row_class(s: str) -> bool:
    return s == "dp-flash" or s.startswith("dp-flash ")


def _find_timestamp(strings: List[str], start: int) -> Optional[str]:
    """Take the first time-looking string after the value cell."""
    n = len(strings)
    for k in range(start, min(start + 6, n)):
        s = strings[k]
        if s in _NOTE_MARKERS or _is_row_class(s):
            return None
        if _is_ws(s) or s in _VALUE_END or s == "style" or s.endswith(";"):
            continue
        if _TIME_RE.search(s):
            return s
        return None
    return None


def _parse_row_body(
    strings: List[str], j: int
) -> tuple:
    """Parse value tokens and timestamp for the sensor key at index ``j``.

    Returns ``(row, next_i)``.  ``row`` is ``None`` when the key carries no
    readable value (note-only row, truncated frame, run into the next row).
    """
    n = len(strings)
    # Collect value tokens (value, optional unit).  8.50 separates them
    # with whitespace strings, 8.51 with css helper classes.
    k = j + 1
    if k < n and _is_ws(strings[k]):
        k += 1  # single leading separator (8.50)
    value_tokens: List[str] = []
    end = None
    while k < n:
        s = strings[k]
        if _is_ws(s) or s in _VALUE_END:
            end = "value"
            break
        if s in _NOTE_MARKERS:
            end = "note"
            break
        if _is_row_class(s) or _KEY_RE.match(s):
            # Ran into the next row (sensor values never look like keys).
            end = "row"
            break
        if len(value_tokens) >= _MAX_VALUE_TOKENS:
            end = "overflow"
            break
        value_tokens.append(s)
        k += 1

    if end != "value":
        # Note-only row, truncated frame or run into the next row: no
        # reading to apply.
        return None, (k if end == "row" else k + 1)

    row = {
        "key": strings[j],
        "value": value_tokens[0] if value_tokens else "",
        "unit": value_tokens[1] if len(value_tokens) > 1 else None,
        "timestamp": _find_timestamp(strings, k + 1),
    }
    return row, k + 1


def extract_changed_rows(strings: List[str]) -> List[Dict[str, Optional[str]]]:
    """Extract changed sensor rows from a decoded string table.

    Returns a list of ``{"key", "value", "unit", "timestamp"}`` dicts, one per
    ``dp-flash`` row that looks like a sensor (dotted key).  Rows without a
    reading (8.51 note-only rows) are skipped so the entity keeps its last
    value.
    """
    rows: List[Dict[str, Optional[str]]] = []
    n = len(strings)
    i = 0
    while i < n:
        if not _is_row_class(strings[i]):
            i += 1
            continue

        # The sensor key is the next non-structural string.
        j = i + 1
        while j < n and (strings[j] in _STRUCTURAL or _is_ws(strings[j])):
            j += 1
        if j >= n:
            break

        key = strings[j]
        # Sensor keys are dotted identifiers (e.g. "Battery.Unit.1.Voltage").
        if not key or "." not in key or " " in key:
            i = j if _is_row_class(key) else j + 1
            continue

        row, i = _parse_row_body(strings, j)
        if row is not None:
            rows.append(row)

    return rows


def extract_initial_rows(
    strings: List[str], known_keys=None
) -> List[Dict[str, Optional[str]]]:
    """Extract sensor rows from a full-page render (no ``dp-flash`` markers).

    On firmware 8.51 the HTTP response of ``/deviceMessages`` contains only
    the pre-rendered "Site Data" card; every device table arrives once as a
    big initial RenderBatch right after the circuit starts (and again after a
    page toggle re-render). Those rows render with an empty css class, so
    :func:`extract_changed_rows` cannot see them. Row starts are detected by
    the dotted-key pattern; ``known_keys`` optionally accepts additional keys
    that do not match it.
    """
    rows: List[Dict[str, Optional[str]]] = []
    n = len(strings)
    i = 0
    while i < n:
        s = strings[i]
        if not isinstance(s, str) or not (
            _KEY_RE.match(s) or (known_keys is not None and s in known_keys)
        ):
            i += 1
            continue
        row, i = _parse_row_body(strings, i)
        if row is not None:
            rows.append(row)
    return rows


def extract_event_handlers(raw: bytes) -> Dict[str, int]:
    """Map DOM element ids to Blazor event handler IDs.

    Scans the reference-frames section of a RenderBatch for attribute frames
    (frame type 3, 20 bytes each: type, name string index, value string index,
    ``int64`` event handler id).  Attributes belong to the element opened by
    the preceding non-attribute frame, so an ``id`` attribute and an event
    handler attribute within the same run identify one clickable element.

    Used to find the ``showUnsupported_*`` / ``showInternal_*`` checkboxes on
    firmware 8.51 so the client can enable them on its own circuit.

    Returns an empty dict on malformed frames - callers treat that as
    "nothing to click".
    """
    strings = parse_render_batch_strings(raw)
    if not strings or len(raw) < 24:
        return {}
    try:
        footer = struct.unpack_from("<5i", raw, len(raw) - 20)
        frames_offset, frames_end = footer[1], footer[2]
        if not (0 <= frames_offset < frames_end <= len(raw)):
            return {}

        pos = frames_offset
        count = struct.unpack_from("<i", raw, pos)[0]
        pos += 4

        handlers: Dict[str, int] = {}
        current_id: Optional[str] = None
        current_event = 0

        def _flush():
            nonlocal current_id, current_event
            if current_id and current_event > 0:
                handlers[current_id] = current_event
            current_id, current_event = None, 0

        for _ in range(count):
            if pos + 20 > frames_end:
                break
            frame_type = struct.unpack_from("<i", raw, pos)[0]
            if frame_type == 3:  # attribute frame
                name_idx = struct.unpack_from("<i", raw, pos + 4)[0]
                value_idx = struct.unpack_from("<i", raw, pos + 8)[0]
                event_id = struct.unpack_from("<q", raw, pos + 12)[0]
                name = strings[name_idx] if 0 <= name_idx < len(strings) else None
                if name == "id" and 0 <= value_idx < len(strings):
                    current_id = strings[value_idx]
                elif event_id > 0:
                    current_event = event_id
            else:
                _flush()
            pos += 20
        _flush()
        return handlers
    except Exception as e:  # noqa: BLE001 - never let a bad frame break the loop
        _LOGGER.debug("[Enpal RenderBatch] event-handler scan failed: %s", e)
        return {}


def extract_change_handler_ids(raw: bytes) -> List[int]:
    """Ordered event handler ids of all ``onchange`` attribute frames.

    Firmware 8.51 disposes and recreates every checkbox handler on each
    re-render.  The diff batches carry the fresh handlers in stable DOM order
    but without ``id`` attributes, so the position in this list is the only
    way to map them back to a checkbox learned from the initial batch.

    Returns an empty list on malformed frames.
    """
    strings = parse_render_batch_strings(raw)
    if not strings or len(raw) < 24:
        return []
    try:
        footer = struct.unpack_from("<5i", raw, len(raw) - 20)
        frames_offset, frames_end = footer[1], footer[2]
        if not (0 <= frames_offset < frames_end <= len(raw)):
            return []

        pos = frames_offset
        count = struct.unpack_from("<i", raw, pos)[0]
        pos += 4

        ordered: List[int] = []
        for _ in range(count):
            if pos + 20 > frames_end:
                break
            frame_type = struct.unpack_from("<i", raw, pos)[0]
            if frame_type == 3:  # attribute frame
                name_idx = struct.unpack_from("<i", raw, pos + 4)[0]
                event_id = struct.unpack_from("<q", raw, pos + 12)[0]
                name = strings[name_idx] if 0 <= name_idx < len(strings) else None
                if name == "onchange" and event_id > 0:
                    ordered.append(event_id)
            pos += 20
        return ordered
    except Exception as e:  # noqa: BLE001 - never let a bad frame break the loop
        _LOGGER.debug("[Enpal RenderBatch] change-handler scan failed: %s", e)
        return []


def is_patchable_value(value: Optional[str]) -> bool:
    """Whether a raw RenderBatch value should be applied on the fast path.

    Empty values and oversized blobs are skipped and left to the full scrape.
    """
    if value is None or value == "":
        return False
    if len(value) > _MAX_VALUE_LEN:
        return False
    return True
