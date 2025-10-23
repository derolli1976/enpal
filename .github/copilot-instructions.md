# Enpal Solar Integration - AI Coding Agent Instructions

## Project Overview
This is a Home Assistant custom integration that parses data from local Enpal solar system web interfaces (e.g., `http://<enpal-box-ip>/deviceMessages`) and creates sensors dynamically. It supports optional wallbox control via an external add-on API.

**Target**: First-generation Enpal boxes that expose HTML tables on local network (NOT all Enpal systems are supported). Enpal boxes get their IP address via DHCP from the router.

## Architecture & Key Components

### Data Flow
1. **HTML Scraping** (`utils.py`): Fetches HTML from Enpal box → BeautifulSoup parsing → extracts sensor data from `<div class="card">` elements
2. **Dynamic Entity Creation** (`sensor.py`, `entity_factory.py`): Parsed data → DataUpdateCoordinator → Auto-generated HA sensor entities
3. **Optional Wallbox Control** (`button.py`, `switch.py`, `select.py`): Only loaded when `use_wallbox_addon=True` → HTTP POST to `localhost:36725/wallbox/*`

### Critical Files
- **`utils.py`**: Core parsing logic (`parse_enpal_html_sensors`, `expand_inverter_system_state`). All sensor extraction happens here.
- **`const.py`**: All constants including `DEFAULT_GROUPS` (sensor categories), unit mappings, device class overrides, icon mappings
- **`entity_factory.py`**: Factory pattern for creating sensor entities with proper device_class/state_class assignments
- **`sensor.py`**: Platform setup with DataUpdateCoordinator, fallback to last known data on errors, cumulative energy sensors
- **`config_flow.py`**: Multi-step UI configuration with auto-discovery and manual setup options, URL validation, group selection, wallbox toggle
- **`discovery.py`**: Network scanning utilities for auto-discovering Enpal boxes on local subnets
- **`wallbox_api.py`**: Centralized API client for all wallbox HTTP communication (added to eliminate code duplication)

### Special Parsing Logic: Inverter System State
The inverter "System State" sensor contains a 200+ character bitfield string like `"State Decimal: 1234 Bits: 0101010101..."`.

**Problem**: String too long (>255 chars) for HA sensor states  
**Solution**: `expand_inverter_system_state()` in `utils.py` splits it into multiple short sensors:
- `sensor.inverter_system_state_decimal` (numeric value)
- `sensor.inverter_system_state_flags` (comma-separated active flags)
- Individual binary state sensors for each bit (e.g., `sensor.inverter_system_state_standby`)

**Detection**: Uses regex `INV_STATE_RE` OR length check `len(value_raw) > 200 and "Bits" in value_raw`

## Development Workflows

### Running Tests
```bash
# Set PYTHONPATH to project root (critical for imports)
$env:PYTHONPATH = "e:\Github\enpal"

# Run all tests
pytest

# Run specific test file
pytest custom_components/enpal_webparser/tests/test_utils.py

# Run with verbose output
pytest -v
```

**Test Structure**:
- `conftest.py`: Fixtures like `real_html` (loads `fixtures/deviceMessages.html`)
- Tests use real HTML fixtures to validate parsing against actual Enpal output
- No mocking of BeautifulSoup - tests parse actual HTML structure

### Adding New Sensors
1. **If sensor appears in HTML but not in HA**: Check if group is enabled in `DEFAULT_GROUPS` (const.py)
2. **Custom unit/device_class**: Add to `DEVICE_CLASS_OVERRIDES` or `STATE_CLASS_OVERRIDES` in `const.py`
3. **Custom icon**: Add mapping to `ICON_MAP` using sensor's `unique_id` format (e.g., `"iotedgedevice_cpu_load": "mdi:cpu-64-bit"`)

### Debugging Sensor Issues
- Check logs with prefix `[Enpal]` - all modules use this
- Sensor unique_ids generated via `make_id()`: lowercase, non-alphanumeric → `_`
- Friendly names created via `friendly_name(group, sensor_name)` - handles special formatting like unit letters in parentheses

## Project-Specific Conventions

### Wallbox API Communication Pattern
All wallbox API calls use the centralized `WallboxApiClient` class (`wallbox_api.py`):
```python
from .wallbox_api import WallboxApiClient

api_client = WallboxApiClient(hass)
success = await api_client.start_charging()  # Returns True/False
data = await api_client.get_status()  # Returns dict or None

# For actions that need sensor refresh:
await api_client.call_and_refresh_sensors(
    "/start",
    sensor_entities=["sensor.wallbox_status"]
)
```

**Key benefits**: Centralized error handling, logging, timeout management, and sensor refresh logic.

### Logging Pattern
```python
_LOGGER.info("[Enpal] Your message: %s", variable)  # Always prefix with [Enpal]
```

### Entity Naming
- **Unique ID**: `make_id("Inverter Power DC Total")` → `"inverter_power_dc_total"`
- **Friendly Name**: `friendly_name("Inverter", "Power.DC.L1")` → `"Inverter: Power DC (L1)"`

### Coordinator Pattern
- Sensors use `DataUpdateCoordinator` with fallback: If fetch fails but `last_successful_data` exists, reuse old values (prevents all sensors going unavailable during transient network issues)
- Wallbox has separate coordinator because it polls different endpoint (`localhost:36725/wallbox/status`)

### Platform Loading
- Base platforms: Always `["sensor"]`
- Optional platforms: `["button", "switch", "select"]` only when `use_wallbox_addon=True`
- Dynamic loading in `__init__.py`: `async_forward_entry_setups(entry, platforms)`

## Integration Points

### External Dependencies
- **BeautifulSoup** (`bs4`): HTML parsing - assumes specific structure with `<div class="card"><h2>GroupName</h2><table><tr><td>Sensor</td><td>Value</td><td>Timestamp</td></tr>`
- **Wallbox Add-on**: Separate Home Assistant add-on (not part of this repo) exposes HTTP API on port 36725
  - Endpoints: `/start`, `/stop`, `/set_eco`, `/set_solar`, `/set_full`, `/status`
  - This integration only consumes the API, doesn't implement it

### Home Assistant Integration
- **Config Flow**: Multi-step UI-only configuration (no YAML)
  - Step 1: Choose between auto-discovery and manual setup
  - Step 2 (discovery): Scan local network subnets for Enpal boxes, present found devices
  - Step 2 (manual): Enter URL manually
  - Step 3: Configure interval, groups, and wallbox addon
- **Network Discovery**: Uses platform-specific detection (ip/ipconfig) to detect actual subnet masks, scans all hosts for `/deviceMessages` endpoint, max 1024 hosts safety limit
- **Restore State**: `DailyResetFromEntitySensor` uses `RestoreEntity` to persist daily energy totals across HA restarts
- **Entity Registry**: Disabled entities for unselected groups still appear in HA (can be manually enabled later)

## Common Pitfalls

1. **255 Character Limit**: HA sensors have state string length limits. Always truncate long values or split them (see inverter system state)
2. **Timestamp Parsing**: Use `ENPAL_TIMESTAMP_FORMAT = "%m/%d/%Y %H:%M:%S"` - Enpal uses MM/DD/YYYY format
3. **Unit Conversion**: Wh → kWh conversion happens in `normalize_value_and_unit()` to match HA energy dashboard expectations
4. **Wallbox Status Dependency**: Switch/select entities listen to `sensor.wallbox_status` state changes - ensure sensor exists before enabling controls
5. **Test Isolation**: Tests don't use pytest parametrize - each test explicitly constructs scenarios for clarity

## Branch Context
Current branch: `72-bug-sensorinverter_system_state-is-longer-than-255`  
Working on: Fixing the inverter system state string length issue (this is why `expand_inverter_system_state()` exists)
