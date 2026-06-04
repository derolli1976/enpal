"""Parser for WebSocket JSON data to Home Assistant sensor format"""
import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

_LOGGER = logging.getLogger(__name__)


def friendly_name(group: str, sensor: str) -> str:
    """
    Format a friendly sensor name with group context.
    
    IMPORTANT: Keep dots in sensor names to match HTML parser format!
    This ensures compatibility with existing automations and dashboards.
    """
    # Keep dots as-is (do NOT replace with spaces)
    # This matches the HTML parser format exactly
    
    # Add group prefix
    return f"{group}: {sensor}" if ':' not in sensor else sensor


def make_id(name: str) -> str:
    """Generate Home Assistant-style unique ID from sensor name"""
    return re.sub(r'[^a-z0-9_]', '_', name.lower())


def parse_timestamp(timestamp_utc: Optional[str]) -> Optional[str]:
    """Convert UTC timestamp to ISO format"""
    if not timestamp_utc:
        return None
    
    try:
        # Already in ISO format
        if 'T' in timestamp_utc and 'Z' in timestamp_utc:
            return timestamp_utc.replace('Z', '+00:00')
        return timestamp_utc
    except Exception as e:
        _LOGGER.debug("[Enpal WebSocket Parser] Timestamp parse error: %s", e)
        return timestamp_utc


def normalize_unit(unit: Optional[str]) -> Optional[str]:
    """Normalize unit names to Home Assistant conventions"""
    if not unit or unit == 'None':
        return None
    
    # Unit mappings
    unit_map = {
        'Celcius': '°C',  # Typo in Enpal data
        'Celsius': '°C',
        'Percent': '%',
        'Wh': 'Wh',
        'kWh': 'kWh',
        'W': 'W',
        'V': 'V',
        'A': 'A',
        'Hz': 'Hz',
    }
    
    return unit_map.get(unit, unit)


def detect_device_class(sensor_name: str, unit: Optional[str], value: Any) -> Optional[str]:
    """Detect Home Assistant device class from sensor name and unit"""
    sensor_lower = sensor_name.lower()
    
    # Energy sensors
    if 'energy' in sensor_lower or 'wh' in str(unit).lower():
        return 'energy'
    
    # Power sensors
    if 'power' in sensor_lower and unit == 'W':
        return 'power'
    
    # Voltage sensors
    if 'voltage' in sensor_lower or unit == 'V':
        return 'voltage'
    
    # Current sensors
    if 'current' in sensor_lower and unit == 'A':
        return 'current'
    
    # Temperature sensors
    if 'temperature' in sensor_lower or unit == '°C':
        return 'temperature'
    
    # Frequency sensors
    if 'frequency' in sensor_lower or unit == 'Hz':
        return 'frequency'
    
    # Battery sensors
    if 'battery' in sensor_lower and 'charge' in sensor_lower and unit == '%':
        return 'battery'
    
    # Signal strength
    if 'rssi' in sensor_lower or 'signal' in sensor_lower:
        return 'signal_strength'
    
    return None


def parse_websocket_json_to_sensors(
    json_data: Dict,
    groups: List[str]
) -> List[Dict[str, Any]]:
    """
    Parse WebSocket JSON data to Home Assistant sensor format.
    
    Returns the same structure as parse_enpal_html_sensors():
    List[Dict[str, Any]] with keys: name, value, unit, device_class, enabled, enpal_last_update, group
    
    Args:
        json_data: WebSocket JSON data (CollectorData)
        groups: List of enabled sensor groups
        
    Returns:
        List of sensor dictionaries
    """
    sensors: List[Dict[str, Any]] = []
    
    # Process DeviceCollections
    for device in json_data.get('DeviceCollections', []):
        device_class_name = device.get('deviceClass', 'Unknown')
        
        # Map JSON deviceClass to HTML group names
        group_mapping = {
            'Battery': 'Battery',
            'Inverter': 'Inverter',
            'IoTEdgeDevice': 'IoTEdgeDevice',
            'PowerSensor': 'PowerSensor',
            'Wallbox': 'Wallbox',
            'Heatpump': 'Heatpump',
        }
        
        group = group_mapping.get(device_class_name, device_class_name)
        
        # Skip if group not enabled
        if group not in groups:
            _LOGGER.debug("[Enpal WebSocket Parser] Skipping group: %s", group)
            continue
        
        # Process number data points
        for json_name, data_point in device.get('numberDataPoints', {}).items():
            sensor = create_sensor_from_datapoint(
                json_name, data_point, group, groups, 'number'
            )
            if sensor:
                sensors.append(sensor)
        
        # Process text data points
        for json_name, data_point in device.get('textDataPoints', {}).items():
            sensor = create_sensor_from_datapoint(
                json_name, data_point, group, groups, 'text'
            )
            if sensor:
                sensors.append(sensor)
    
    # Process top-level numberDataPoints and textDataPoints (Site Data)
    if 'Site Data' in groups:
        for json_name, data_point in json_data.get('numberDataPoints', {}).items():
            sensor = create_sensor_from_datapoint(
                json_name, data_point, 'Site Data', groups, 'number'
            )
            if sensor:
                sensors.append(sensor)
        
        for json_name, data_point in json_data.get('textDataPoints', {}).items():
            sensor = create_sensor_from_datapoint(
                json_name, data_point, 'Site Data', groups, 'text'
            )
            if sensor:
                sensors.append(sensor)
    
    # Process EnergyManagement (Wallbox energy sources)
    if 'Wallbox' in groups:
        for em in json_data.get('EnergyManagement', []):
            for json_name, data_point in em.get('numberDataPoints', {}).items():
                sensor = create_sensor_from_datapoint(
                    json_name, data_point, 'Wallbox', groups, 'number'
                )
                if sensor:
                    sensors.append(sensor)
    
    _LOGGER.info(
        "[Enpal WebSocket Parser] Parsed %d sensors from WebSocket data",
        len(sensors)
    )
    
    return sensors


def create_sensor_from_datapoint(
    json_name: str,
    data_point: Dict,
    group: str,
    groups: List[str],
    data_type: str
) -> Optional[Dict[str, Any]]:
    """
    Create a sensor dictionary from a WebSocket data point.
    
    Args:
        json_name: JSON sensor name (e.g., "Energy.Battery.Charge.Level")
        data_point: Data point dict with value, unit, timestamp
        group: Sensor group name
        groups: List of enabled groups
        data_type: 'number' or 'text'
        
    Returns:
        Sensor dictionary or None
    """
    try:
        value = data_point.get('value')
        unit_raw = data_point.get('unit')
        timestamp_utc = data_point.get('timeStampUtcOfMeasurement')
        
        # Normalize unit
        unit = normalize_unit(unit_raw)
        
        # Convert Wh to kWh for energy sensors (like HTML parser does)
        if unit == 'Wh' and isinstance(value, (int, float)):
            value = value / 1000.0
            unit = 'kWh'
        
        # Convert value to string for consistency
        if isinstance(value, float):
            # Format float with appropriate precision
            if abs(value) < 0.01:
                value_str = f"{value:.4f}"
            elif abs(value) < 1:
                value_str = f"{value:.3f}"
            elif abs(value) < 10:
                value_str = f"{value:.2f}"
            elif abs(value) < 100:
                value_str = f"{value:.1f}"
            else:
                value_str = f"{value:.0f}"
        else:
            value_str = str(value)
        
        # Generate friendly name
        sensor_name = friendly_name(group, json_name)
        
        # Detect device class
        device_class = detect_device_class(json_name, unit, value)
        
        # Parse timestamp
        timestamp_iso = parse_timestamp(timestamp_utc)
        
        # Create sensor dict (same format as HTML parser)
        sensor = {
            'name': sensor_name,
            'value': value_str,
            'unit': unit,
            'device_class': device_class,
            'enabled': group in groups,
            'enpal_last_update': timestamp_iso,
            'group': group,
        }
        
        return sensor
        
    except Exception as e:
        _LOGGER.warning(
            "[Enpal WebSocket Parser] Failed to parse sensor %s: %s",
            json_name, e
        )
        return None
