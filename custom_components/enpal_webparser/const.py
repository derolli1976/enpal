#
# Home Assistant Custom Component: Enpal Webparser
#
# File: const.py
#
# Description:
#   Shared constants for the Enpal Webparser integration.
#   Stores domain, default URLs, groups, unit mappings, and wallbox settings.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
# Repository:   https://github.com/derolli1976/enpal
#
# Compatible with Home Assistant Core 2024.x and later.
#
# See README.md for setup and usage instructions.
#

# --- Domain & Integration Info ---
DOMAIN = "enpal_webparser"

# --- Default Connection Settings ---
DEFAULT_URL = "http://192.168.178.178/deviceMessages"
DEFAULT_INTERVAL = 60
DEFAULT_GROUPS = [
    "Wallbox",
    "Battery",
    "Inverter",
    "Site Data",
    "IoTEdgeDevice",
    "PowerSensor",
]
DEFAULT_USE_WALLBOX_ADDON = False
DEFAULT_WALLBOX_API_ENDPOINT = "http://localhost:36725/wallbox"

# --- Device Class/Unit Mappings ---
DEFAULT_UNITS = {
    "power": "W",
    "energy": "kWh",
    "voltage": "V",
    "current": "A",
    "temperature": "°C",
    "frequency": "Hz",
}

UNIT_DEVICE_CLASS_MAP = {
    "kWh": "energy",
    "Wh": "energy",
    "kW": "power",
    "W": "power",
    "V": "voltage",
    "A": "current",
    "Hz": "frequency",
    "°C": "temperature",
    "%": None,
}

# --- Wallbox Mode Mapping ---
WALLBOX_MODE_MAP = {
    "eco": "Eco",
    "fast": "Full",
    "solar": "Solar",
}

# --- Date/Time Formats ---
ENPAL_TIMESTAMP_FORMAT = "%m/%d/%Y %H:%M:%S"
