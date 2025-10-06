#
# Home Assistant Custom Component: Enpal Webparser
#
# File: utils.py
#
# Description:
#   Shared utility functions for the Enpal Webparser integration.
#   Provides helpers for parsing, ID generation, unit normalization, and more.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
# Repository:   https://github.com/derolli1976/enpal
#
# Compatible with Home Assistant Core 2024.x and later.
#
# See README.md for setup and usage instructions.
#

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from .const import (
    DEFAULT_UNITS,
    DEVICE_CLASS_OVERRIDES,
    ENPAL_TIMESTAMP_FORMAT,
    UNIT_DEVICE_CLASS_MAP,
)



def make_id(name: str) -> str:
    """Generate a Home Assistant-friendly unique id from a name."""
    name = name.lower()
    name = re.sub(r"[^\w]+", "_", name)
    return name.strip("_")


def is_strict_number(s: str) -> bool:
    s2 = s.strip().replace(',', '.')
    return bool(re.fullmatch(r'[-+]?\d+(\.\d+)?', s2))


def friendly_name(group: str, sensor: str) -> str:
    """Format a friendly sensor name with group context."""
    group_lower = group.lower()
    parts = sensor.split('.')
    label = []
    skip_next = False

    for i, part in enumerate(parts):
        if i + 1 < len(parts) and re.fullmatch(r"[A-Z]", parts[i + 1]):
            label.append(f"{part} ({parts[i + 1]})")
            skip_next = True
        elif skip_next:
            skip_next = False
        else:
            label.append(part)

    full_label = ' '.join(label)
    return full_label if group_lower in full_label.lower() else f"{group}: {full_label}"


def get_numeric_value(value: str) -> str:
    """Extract the numeric portion of a string (supports float with dot or comma)."""
    match = re.search(r"[-+]?[0-9]*\.?[0-9]+", value.replace(',', '.'))
    return match.group(0) if match else value


def get_class_and_unit(
    value: str,
    unit_device_class_map: Dict[str, str],
) -> Tuple[Optional[str], Optional[str]]:
    """Detect the unit and device_class for a given value string."""
    value = value.strip()
    for unit, device_class in unit_device_class_map.items():
        if value.endswith(unit):
            return unit, device_class
    return None, None


def normalize_value_and_unit(
    value_raw: str,
    unit: Optional[str],
    device_class: Optional[str],
    default_units: Dict[str, str],
) -> Tuple[str, Optional[str]]:
    """
    Normalize the value and unit:
      - Convert Wh to kWh if necessary.
      - Fallback to default unit if unit is missing but device_class is known.
    Returns: value (str), unit (str or None)
    """

    # determine if the context is suggesting a numeric value
    numeric_device_classes = {
        "energy", "power", "voltage", "current", "temperature",
        "frequency", "battery", "humidity", "pressure"
    }
    numeric_context = (unit is not None) or (device_class in numeric_device_classes) or is_strict_number(value_raw)

    if not numeric_context:
        # not a numeric context, return raw value and no unit
        return value_raw, None

    value_clean = get_numeric_value(value_raw)
    unit_out = unit

    # convert Wh to kWh if applicable
    if unit == "Wh":
        try:
            value_clean = str(round(float(value_clean) / 1000, 3))
            unit_out = "kWh"
        except ValueError:
            pass

    # fallback to default unit if missing
    if device_class and not unit_out:
        unit_out = default_units.get(device_class)

    return value_clean, unit_out


def parse_enpal_html_sensors(
    html: str,
    groups: List[str]
) -> List[Dict[str, Any]]:
    """parsing the html content and extracting sensor data."""
    soup = BeautifulSoup(html, 'html.parser')
    sensors = []

    for card in soup.find_all("div", class_="card"):
        if not isinstance(card, Tag):
            continue

        group = extract_group_from_card(card)
        if not group or group not in groups:
            continue

        sensors.extend(parse_card_rows(card, group, groups))

    return sensors


def extract_group_from_card(card: Tag) -> Optional[str]:
    """Reads the group name from a Card header (h2)."""
    h2_tag = card.find("h2")
    return h2_tag.text.strip() if h2_tag else None


def parse_card_rows(card: Tag, group: str, groups: List[str]) -> List[Dict[str, Any]]:
    """Extracts sensors from a group."""
    rows = card.find_all("tr")[1:]  # assume first row == header
    sensor_list = []

    for row in rows:
        if not isinstance(row, Tag):
            continue

        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        raw_name = cols[0].text.strip()
        value_raw = cols[1].text.strip()
        timestamp_str = cols[2].text.strip() if len(cols) > 2 else None

        unit, device_class = get_class_and_unit(value_raw, UNIT_DEVICE_CLASS_MAP)
        value_clean, unit = normalize_value_and_unit(value_raw, unit, device_class, DEFAULT_UNITS)
        timestamp_iso = parse_timestamp(timestamp_str)

        sensor = {
            "name": friendly_name(group, raw_name),
            "value": value_clean,
            "unit": unit,
            "device_class": device_class,
            "enabled": group in groups,
            "enpal_last_update": timestamp_iso,
        }

        sensor_id = make_id(sensor["name"])
        if sensor_id in DEVICE_CLASS_OVERRIDES:
            sensor["device_class"] = DEVICE_CLASS_OVERRIDES[sensor_id]

        sensor_list.append(sensor)

    return sensor_list


def parse_timestamp(raw: Optional[str]) -> Optional[str]:
    """Converts a timestamp (i.g. 06.06.2025 08:42) to ISO-Format."""
    if not raw:
        return None
    try:
        dt = datetime.strptime(raw, ENPAL_TIMESTAMP_FORMAT)
        return dt.isoformat()
    except ValueError:
        return raw
