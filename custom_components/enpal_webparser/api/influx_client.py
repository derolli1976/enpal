"""InfluxDB client for the Enpal Box (expert data source).

Enpal boxes run an InfluxDB 2.x on port 8086 (verified: v2.8.0). Access token
and organisation are provided by Enpal on request. The bucket "solar" holds
one series per data point: measurement = device card (battery, inverter, iot,
powerSensor, system, wallbox), field = the same dotted key that /deviceMessages
uses (e.g. "Power.DC.Total"), plus a "unit" tag.

The client polls the last value of every series with a single Flux query and
maps the rows onto the shared sensor-dict format. Group and entity-id
resolution mirrors the WebSocket client (SENSOR_KEY_ALIASES → SENSOR_KEY_GROUPS
→ measurement fallback), so switching the data source keeps the entity ids.

String values (wallbox status/mode, serial numbers) are not stored in InfluxDB;
wallbox control and status keep using the Blazor client independently.
"""

import asyncio
import csv
import logging
import re
import urllib.parse
from typing import Dict, List, Optional

import aiohttp

from .base import EnpalApiClient

_LOGGER = logging.getLogger(__name__)

DEFAULT_INFLUX_PORT = 8086
DEFAULT_INFLUX_BUCKET = "solar"

# Flux range for the last-value query. Series that had no point in this window
# are treated as stale and skipped (mirrors the page dropping outdated rows).
_QUERY_RANGE = "-2h"

_QUERY_TIMEOUT = aiohttp.ClientTimeout(total=30)

# Influx measurement -> card group of the /deviceMessages page. Fallback for
# keys that are not in SENSOR_KEY_GROUPS (e.g. the Influx-only "system" keys
# like Power.Production.Total).
MEASUREMENT_GROUPS = {
    "battery": "Battery",
    "inverter": "Inverter",
    "iot": "IoTEdgeDevice",
    "powerSensor": "PowerSensor",
    "system": "Site Data",
    "wallbox": "Wallbox",
    "heatpump": "Heatpump",
    "controlBox": "ControlBox",
}

# Influx "unit" tag -> unit string as the HTML page renders it. Values run
# through the same get_class_and_unit/normalize pipeline as the other clients
# afterwards (including Wh -> kWh conversion).
_UNIT_TAG_MAP = {
    "Percent": "%",
    "Celcius": "°C",  # sic - Enpal's spelling in the unit tag
    "Celsius": "°C",
    "None": None,
    "": None,
}

# Real data-point keys are dotted and start with a letter; skips internal
# fields such as "measureId".
_FIELD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(\.[A-Za-z0-9]+)+$")


def parse_influx_csv(body: str) -> List[Dict[str, str]]:
    """Parse an annotated Flux CSV response into a list of row dicts.

    Tolerant of the real-world format: annotation lines starting with '#',
    blank lines between data rows, and repeated header rows for multiple
    result tables. Defensive: returns [] for empty or malformed bodies.
    """
    rows: List[Dict[str, str]] = []
    header: Optional[str] = None
    block: List[str] = []

    def _flush() -> None:
        if header and block:
            rows.extend(
                row for row in csv.DictReader([header] + block)
                if row.get("_field") and row.get("_value") is not None
            )

    for line in (body or "").splitlines():
        line = line.strip("\r")
        if not line.strip() or line.startswith("#"):
            continue
        if "_field" in line and "_value" in line and "_measurement" in line:
            _flush()
            header = line
            block = []
        elif header:
            block.append(line)
    _flush()
    return rows


def _format_number(value: str) -> str:
    """Trim float noise from Influx values (e.g. 40.699999999999996 -> 40.7)."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return value
    if f == int(f):
        return str(int(f))
    return repr(round(f, 3))


class EnpalInfluxClient(EnpalApiClient):
    """Polling client that reads sensor values from the box's InfluxDB."""

    def __init__(
        self,
        base_url: str,
        token: str,
        org: str,
        bucket: str = DEFAULT_INFLUX_BUCKET,
        port: int = DEFAULT_INFLUX_PORT,
        excluded_groups: Optional[List[str]] = None,
    ):
        host = base_url.replace("http://", "").replace("https://", "")
        host = host.split("/")[0].split(":")[0]
        self.influx_url = f"http://{host}:{port}"
        self._token = token
        self._org = org
        self._bucket = bucket
        self.excluded_groups = list(excluded_groups or [])
        self.session: Optional[aiohttp.ClientSession] = None
        self.connected = False

    # ------------------------------------------------------------------
    # EnpalApiClient interface
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Open a session and validate reachability, token and bucket."""
        await self.close()
        try:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Token {self._token}"},
                connector=aiohttp.TCPConnector(use_dns_cache=False),
            )
            async with self.session.get(
                f"{self.influx_url}/health", timeout=_QUERY_TIMEOUT
            ) as resp:
                if resp.status != 200:
                    raise ValueError(f"InfluxDB health check failed: HTTP {resp.status}")
            # Cheap authenticated call to fail fast on a wrong token/org.
            body = await self._query(
                f'from(bucket: "{self._bucket}") |> range(start: -5m) |> limit(n: 1)'
            )
            if body is None:
                raise ValueError("InfluxDB test query failed")
            self.connected = True
            _LOGGER.info(
                "[Enpal InfluxDB] Connected to %s (org=%s, bucket=%s)",
                self.influx_url, self._org, self._bucket,
            )
            return True
        except Exception as e:
            _LOGGER.error("[Enpal InfluxDB] Connection failed: %s", e)
            await self.close()
            return False

    async def fetch_data(self) -> Dict:
        """Fetch the last value of every series and map it to sensor dicts."""
        if not self.connected:
            raise RuntimeError("Not connected to InfluxDB")
        body = await self._query(
            f'from(bucket: "{self._bucket}") '
            f'|> range(start: {_QUERY_RANGE}) '
            f'|> last()'
        )
        if body is None:
            self.connected = False
            raise RuntimeError("InfluxDB query failed")
        rows = parse_influx_csv(body)
        sensors = self.sensors_from_rows(rows)
        _LOGGER.debug(
            "[Enpal InfluxDB] %d series -> %d sensors", len(rows), len(sensors)
        )
        return {"sensors": sensors, "source": "influxdb"}

    async def close(self) -> None:
        self.connected = False
        if self.session and not self.session.closed:
            try:
                await self.session.close()
            except Exception:
                pass
        self.session = None

    def is_connected(self) -> bool:
        return self.connected and self.session is not None and not self.session.closed

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _query(self, flux: str) -> Optional[str]:
        """POST a Flux query; returns the CSV body or None on failure."""
        url = (
            f"{self.influx_url}/api/v2/query?org="
            f"{urllib.parse.quote(self._org)}"
        )
        try:
            async with self.session.post(
                url,
                data=flux.encode("utf-8"),
                headers={"Content-Type": "application/vnd.flux"},
                timeout=_QUERY_TIMEOUT,
            ) as resp:
                if resp.status == 401:
                    _LOGGER.error("[Enpal InfluxDB] Unauthorized - check token")
                    return None
                if resp.status != 200:
                    _LOGGER.error(
                        "[Enpal InfluxDB] Query failed: HTTP %s", resp.status
                    )
                    return None
                return await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            _LOGGER.error("[Enpal InfluxDB] Query error: %s", e)
            return None

    def sensors_from_rows(self, rows: List[Dict[str, str]]) -> List[Dict]:
        """Convert Influx series rows into the shared sensor-dict format.

        Group and name resolution mirrors the WebSocket client so that
        switching the data source keeps the entity ids. Duplicate series
        (the box writes some keys into two measurements) collapse into one
        sensor; the first occurrence wins.
        """
        from ..utils import (
            make_id,
            friendly_name,
            get_class_and_unit,
            normalize_value_and_unit,
            expand_inverter_system_state,
        )
        from ..const import (
            DEFAULT_UNITS,
            DEVICE_CLASS_OVERRIDES,
            SENSOR_KEY_ALIASES,
            SENSOR_KEY_GROUPS,
            UNIT_DEVICE_CLASS_MAP,
        )

        sensors: List[Dict] = []
        seen_ids: set = set()

        def _add(sensor: Dict) -> None:
            uid = make_id(sensor.get("name", ""))
            if not uid or uid in seen_ids:
                return
            seen_ids.add(uid)
            sensors.append(sensor)

        for row in rows:
            raw_key = row.get("_field", "")
            if not _FIELD_RE.match(raw_key):
                continue
            key = SENSOR_KEY_ALIASES.get(raw_key, raw_key)
            group = (
                SENSOR_KEY_GROUPS.get(raw_key)
                or SENSOR_KEY_GROUPS.get(key)
                or MEASUREMENT_GROUPS.get(row.get("_measurement", ""))
                or "Uncategorized"
            )
            enabled = group not in self.excluded_groups
            timestamp = row.get("_time") or None
            value = _format_number(row.get("_value", ""))

            # System state arrives as a plain decimal here; synthesize the
            # bitfield text so the same split sensors as WS/HTML mode emerge.
            if key == "Inverter.System.State":
                try:
                    decimal = int(float(value))
                except (TypeError, ValueError):
                    continue
                text = f"Decimal: {decimal} Bits: {decimal:010b}"
                _add({
                    "name": friendly_name(group, key),
                    "value": text[:240],
                    "unit": None,
                    "device_class": None,
                    "enabled": enabled,
                    "enpal_last_update": timestamp,
                    "group": group,
                })
                for expanded in expand_inverter_system_state(group, text, timestamp):
                    expanded["enabled"] = enabled
                    expanded["raw_key"] = raw_key
                    _add(expanded)
                continue

            unit_tag = row.get("unit", "")
            unit_raw = _UNIT_TAG_MAP.get(unit_tag, unit_tag) or None
            combined = f"{value}{unit_raw}" if unit_raw else value
            unit, device_class = get_class_and_unit(combined, UNIT_DEVICE_CLASS_MAP)
            value_clean, unit = normalize_value_and_unit(
                combined, unit, device_class, DEFAULT_UNITS
            )

            sensor = {
                "name": friendly_name(group, key),
                "value": value_clean,
                "unit": unit,
                "device_class": device_class,
                "enabled": enabled,
                "enpal_last_update": timestamp,
                "group": group,
                "raw_key": raw_key,
            }
            uid = make_id(sensor["name"])
            if uid in DEVICE_CLASS_OVERRIDES:
                sensor["device_class"] = DEVICE_CLASS_OVERRIDES[uid]
            _add(sensor)

        return sensors
