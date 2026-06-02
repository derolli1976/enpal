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
DOM order, as the following run of strings::

    'dp-flash', '<Key>', '<ws>', '<value>'[, '<unit>'], '<ws>', '<timestamp>'

where ``<ws>`` is a pure-whitespace separator.  Recovering the changed rows is
therefore a simple linear scan over the decoded string table - no virtual DOM
reconstruction required.

This is a best-effort fast path.  Anything it cannot resolve (ambiguous keys,
brand-new sensors, malformed frames) is left to the periodic full HTML scrape
the coordinator already performs, so the worst case degrades gracefully to
plain interval polling.
"""

import io
import struct
import logging
from typing import Dict, List, Optional

_LOGGER = logging.getLogger(__name__)

# Strings that frame a sensor row but carry no data themselves.
_STRUCTURAL = {"onchange", "tr", "td", "class", "dp-flash", ""}

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


def extract_changed_rows(strings: List[str]) -> List[Dict[str, Optional[str]]]:
    """Extract changed sensor rows from a decoded string table.

    Returns a list of ``{"key", "value", "unit", "timestamp"}`` dicts, one per
    ``dp-flash`` row that looks like a sensor (dotted key).
    """
    rows: List[Dict[str, Optional[str]]] = []
    n = len(strings)
    i = 0
    while i < n:
        if strings[i] != "dp-flash":
            i += 1
            continue

        # The sensor key is the next non-structural string.
        j = i + 1
        while j < n and strings[j] in _STRUCTURAL:
            j += 1
        if j >= n:
            break

        key = strings[j]
        # Sensor keys are dotted identifiers (e.g. "Battery.Unit.1.Voltage").
        if not key or _is_ws(key) or "." not in key:
            i = j
            continue

        # Advance to the first whitespace separator after the key.
        k = j + 1
        while k < n and not _is_ws(strings[k]):
            k += 1
        # Collect value tokens (value, optional unit) until the next separator.
        k += 1
        value_tokens: List[str] = []
        while k < n and not _is_ws(strings[k]):
            value_tokens.append(strings[k])
            k += 1
        # The timestamp follows the second whitespace separator.
        k += 1
        timestamp = strings[k] if k < n else None

        rows.append({
            "key": key,
            "value": value_tokens[0] if value_tokens else "",
            "unit": value_tokens[1] if len(value_tokens) > 1 else None,
            "timestamp": timestamp,
        })
        i = k + 1

    return rows


def is_patchable_value(value: Optional[str]) -> bool:
    """Whether a raw RenderBatch value should be applied on the fast path.

    Empty values and oversized blobs are skipped and left to the full scrape.
    """
    if value is None or value == "":
        return False
    if len(value) > _MAX_VALUE_LEN:
        return False
    return True
