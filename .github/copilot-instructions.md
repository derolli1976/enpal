# Enpal Solar Integration - AI Coding Agent Instructions

## Project Overview
This is a Home Assistant custom integration that reads data from local Enpal solar systems and creates sensors dynamically. It supports two data sources and optional wallbox control.

**Target**: First-generation Enpal boxes that expose a local web interface (NOT all Enpal systems are supported). Enpal boxes get their IP address via DHCP from the router.

**Two data-source modes** (chosen in the config flow, stored as `data_source` = `html` / `websocket` / `auto`):
- **HTML mode (Legacy)**: Periodically scrapes `http://<enpal-box-ip>/deviceMessages` and parses the HTML tables.
- **WebSocket mode (Firmware 8.50)**: Connects to the box's Blazor SignalR WebSocket for real-time data and native wallbox control (no add-on required).

**Firmware dependency**: The WebSocket mode, native wallbox control, and the incremental RenderBatch parsing require Enpal firmware **Solar Rel. 8.50** (tested with `8.50.1-773465`). Older firmware keeps working in HTML mode only.

## Architecture & Key Components

### Data Flow
1. **HTML Scraping** (`utils.py`): Fetches HTML from Enpal box → BeautifulSoup parsing → extracts sensor data from `<div class="card">` elements
2. **WebSocket / RenderBatch** (`api/websocket_client.py`, `api/render_batch.py`): Blazor SignalR push → incremental binary RenderBatch diff → patches a cached sensor baseline in real time
3. **Dynamic Entity Creation** (`sensor.py`, `entity_factory.py`): Parsed data → DataUpdateCoordinator → Auto-generated HA sensor entities (created at runtime as new keys appear, values retained when keys disappear)
4. **Wallbox Control** (`button.py`, `switch.py`, `select.py` + `wallbox_api.py`): Native (Blazor click) in WebSocket mode, or legacy HTTP POST to `localhost:36725/wallbox/*` via the add-on

### Critical Files
- **`utils.py`**: Core parsing logic (`parse_enpal_html_sensors`, `expand_inverter_system_state`). All sensor extraction happens here.
- **`const.py`**: All constants including `DEFAULT_GROUPS` (sensor categories), unit mappings, device class overrides, icon mappings
- **`entity_factory.py`**: Factory pattern for creating sensor entities with proper device_class/state_class assignments
- **`sensor.py`**: Platform setup with DataUpdateCoordinator, fallback to last known data on errors, cumulative energy sensors
- **`config_flow.py`**: Multi-step UI configuration with auto-discovery and manual setup options, URL validation, group selection, wallbox toggle
- **`discovery.py`**: Network scanning utilities for auto-discovering Enpal boxes on local subnets
- **`repairs.py`**: HA repair flow. Surfaces a fixable issue when wallbox control is enabled but no wallbox status source could be auto-detected; the flow lets the user pick the raw sensor and writes it to the `wallbox_status_source` option (see below)
- **`wallbox_api.py`**: Centralized API client for all wallbox communication. Blazor-first (`_control`) with add-on (port 36725) fallback; not coupled to `use_native`
- **`api/websocket_client.py`**: Blazor SignalR client. Connect/handshake, ping loop, message read loop. Handles `JS.RenderBatch` pushes incrementally (see below) and exposes `_scrape_and_parse()` as the full-scrape baseline source
- **`api/render_batch.py`**: Decodes the Blazor RenderBatch binary payload (`parse_render_batch_strings`, `extract_changed_rows`, `is_patchable_value`). Pure functions, defensive: returns `[]` on malformed/empty frames
- **`api/wallbox_client.py`**, **`api/websocket_parser.py`**, **`api/html_client.py`**, **`api/protocol.py`**, **`api/base.py`**: Blazor button clicks, WebSocket payload parsing, HTTP client, SignalR/MessagePack protocol helpers, shared base

### WebSocket Incremental RenderBatch Parsing (Firmware 8.50)
In WebSocket mode the box pushes a binary Blazor RenderBatch on every change (~every 5 s). Instead of re-scraping the full page each time, `websocket_client._on_render_batch` patches a cached baseline incrementally.

- **Binary layout** (see `render_batch.py` docstring): last 4 bytes = int32 LE string-table offset; the table is an array of int32 offsets to VLQ-length-prefixed UTF-8 strings.
- **Row pattern** per changed sensor (DOM order): `'dp-flash', '<DottedKey>', '<ws>', '<value>'[, '<unit>'], '<ws>', '<timestamp>'`. A linear scan is enough; no virtual-DOM reconstruction.
- **Fast path** (`_apply_diff`): only patches unambiguous keys (`_key_index[make_id(key)]` has exactly 1 index). Reuses `get_class_and_unit` + `normalize_value_and_unit` so values match the HTML parser (e.g. Wh→kWh).
- **Slow path / safety net**: the coordinator's existing periodic full scrape (`fetch_data()` → `_set_baseline`, default 60 s) refreshes the baseline and corrects ambiguous/new/oversized rows.
- **Deliberately skipped on the fast path** (handled by the full scrape): ~10 ambiguous keys whose dotted name appears in two groups (e.g. `power_ac_phase_a/b/c`, `voltage_phase_a/b/c` in Inverter+PowerSensor; `power_battery_charge_discharge` etc. in Inverter+Battery), empty values, and values >200 chars (inverter system state).
- **Worst case** degrades gracefully to plain interval polling (= current HTML behavior).

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
- Optional platforms: `["button", "switch", "select"]` when wallbox control is enabled (native in WebSocket mode, or via add-on in HTML mode)
- Dynamic loading in `__init__.py`: `async_forward_entry_setups(entry, platforms)`

## Integration Points

### External Dependencies
- **BeautifulSoup** (`bs4`): HTML parsing - assumes specific structure with `<div class="card"><h2>GroupName</h2><table><tr><td>Sensor</td><td>Value</td><td>Timestamp</td></tr>`
- **Wallbox Add-on (Legacy / HTML mode only)**: Separate Home Assistant add-on (not part of this repo) exposes HTTP API on port 36725
  - Endpoints: `/start`, `/stop`, `/set_eco`, `/set_solar`, `/set_full`, `/status`
  - This integration only consumes the API, doesn't implement it
  - In WebSocket mode (Firmware 8.50) the add-on is NOT needed; the integration controls the wallbox natively via Blazor. The add-on should be stopped to avoid duplicate commands.

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
5. **Wallbox status source naming varies by firmware**: The raw status sensor can be `Status.Wallbox.Connector.1` (→ `status_wallbox_connector_1`) or `Status.Connector.1` (→ `wallbox_status_connector_1`, e.g. Enpal ArC GEN2). Both are in `WALLBOX_STATUS_SOURCE_CANDIDATES` (`const.py`). `Status.Wallbox.Connected` (1/0 attach flag) is intentionally NOT a candidate. If auto-detect fails, `sensor.py` `_manage_wallbox_status_issue()` raises a repair issue and `repairs.py` lets the user pick the source.
6. **Test Isolation**: Tests don't use pytest parametrize - each test explicitly constructs scenarios for clarity

## Branch Context
Current branch: issue-127 fix branch (manifest version `2.9.9b4`).
Recent work: Firmware-8.50 adaptation (WebSocket/native wallbox mode, dynamic runtime sensor creation with `RestoreEntity`, incremental RenderBatch parsing). 2.9.9b4 adds the second wallbox status candidate (`wallbox_status_connector_1`) and an HA repair issue + fix flow (`repairs.py`) for unresolved wallbox status sources.

## Documentation Writing Style (README, Release Notes, German user-facing docs)
User-facing docs are written in German. Avoid AI-typical phrasing and "AI slop". Target style: short, concrete declarative sentences.

**Avoid:**
- Tricolons / "nicht nur X, sondern auch Y und Z" and other symmetric/parallel sentence patterns
- Filler and escalation phrases: "Genau hier/dort beginnt", "Damit wird deutlich", "Die eigentliche Frage", "entscheidend ist", "Mehrwert schaffen", "Potenziale heben", "in einer zunehmend komplexen Welt", "in der heutigen schnelllebigen Welt", "es ist wichtig zu beachten", "jetzt wird es richtig spannend"
- Stacked transitions like repeated "zudem / darüber hinaus"
- Em-dashes and en-dashes (—/–); use a period, comma, or restructure the sentence instead
- Inflated marketing words ("deutlich", "unbedingt", "ganz ohne") and "Vorteile auf einen Blick"-style headers

**Prefer:** plain statements of what changed and why, one idea per sentence, consistent "du"-address in instructions.
