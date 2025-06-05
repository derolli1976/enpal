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
