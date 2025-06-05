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
from typing import Optional, Tuple, Dict
from bs4 import BeautifulSoup, Tag
from datetime import datetime
from typing import List, Dict, Any, Optional

from .const import (
    UNIT_DEVICE_CLASS_MAP, ENPAL_TIMESTAMP_FORMAT,DEFAULT_UNITS)

def make_id(name: str) -> str:
    """Generate a Home Assistant-friendly unique id from a name."""
    name = name.lower()
    name = re.sub(r"[^\w]+", "_", name)
    return name.strip("_")

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
    value_clean = get_numeric_value(value_raw)
    unit_out = unit

    # Wh zu kWh konvertieren
    if unit == "Wh":
        try:
            value_clean = str(round(float(value_clean) / 1000, 3))
            unit_out = "kWh"
        except ValueError:
            pass

    # Fallback: Wenn device_class bekannt, aber unit fehlt
    if device_class and not unit_out:
        unit_out = default_units.get(device_class)

    return value_clean, unit_out


def parse_enpal_html_sensors(
    html: str, 
    groups: list[str]
) -> List[Dict[str, Any]]:
    """Parst Enpal HTML und liefert Sensor-Data-Listen für Home Assistant."""
    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.find_all("div", class_="card")
    sensors = []
    for card in cards:
        if not isinstance(card, Tag):
            continue
        h2_tag = card.find("h2")
        if h2_tag is not None:
            group = h2_tag.text.strip()
        else:
            continue
        if group not in groups:
            continue

        rows = card.find_all("tr")[1:]
        for row in rows:
            if not isinstance(row, Tag):
                continue
            cols = row.find_all("td")
            if len(cols) >= 2:
                raw_name = cols[0].text.strip()
                value_raw = cols[1].text.strip()
                unit, device_class = get_class_and_unit(value_raw, UNIT_DEVICE_CLASS_MAP)
                value_clean, unit = normalize_value_and_unit(value_raw, unit, device_class, DEFAULT_UNITS)

                timestamp_str = cols[2].text.strip() if len(cols) > 2 else None
                timestamp_iso = None
                if timestamp_str:
                    try:
                        dt = datetime.strptime(timestamp_str, ENPAL_TIMESTAMP_FORMAT)
                        timestamp_iso = dt.isoformat()
                    except ValueError:
                        timestamp_iso = timestamp_str

                sensor_data = {
                    "name": friendly_name(group, raw_name),
                    "value": value_clean,
                    "unit": unit,
                    "device_class": device_class,
                    "enabled": group in groups,
                    "enpal_last_update": timestamp_iso,
                }
                sensors.append(sensor_data)
    return sensors
