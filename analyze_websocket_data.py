#!/usr/bin/env python3
"""
Analyze WebSocket JSON data and compare with HTML Parser sensor names.

This script:
1. Reads websocket_poc_data.json
2. Extracts all sensor names from JSON (numberDataPoints + textDataPoints)
3. Converts them to expected HTML parser sensor names
4. Compares with actual HTML parser patterns
5. Reports matches, mismatches, and new sensors
"""
import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


def make_id(name: str) -> str:
    """Generate Home Assistant-style unique ID from sensor name"""
    return re.sub(r'[^a-z0-9_]', '_', name.lower())


def friendly_name(group: str, sensor: str) -> str:
    """Format a friendly sensor name with group context"""
    # Replace dots with spaces
    sensor = sensor.replace('.', ' ')
    
    # Handle letters in parentheses (e.g., "Phase A" -> "Phase (A)")
    sensor = re.sub(r'\s([A-C]|[123])\b', r' (\1)', sensor)
    
    # Add group prefix
    return f"{group}: {sensor}" if ':' not in sensor else sensor


def extract_sensors_from_json(json_data: dict) -> Dict[str, List[Dict]]:
    """
    Extract all sensors from WebSocket JSON data.
    
    Returns:
        Dict with structure: {
            'Battery': [{'name': 'Energy.Battery.Charge.Level', 'type': 'number', 'value': 76.0, ...}],
            'Inverter': [...],
            ...
        }
    """
    sensors_by_group = {}
    
    # Process DeviceCollections
    for device in json_data.get('DeviceCollections', []):
        device_class = device.get('deviceClass', 'Unknown')
        sensors = []
        
        # Number data points
        for name, data_point in device.get('numberDataPoints', {}).items():
            sensors.append({
                'name': name,
                'type': 'number',
                'value': data_point.get('value'),
                'unit': data_point.get('unit'),
                'timestamp': data_point.get('timeStampUtcOfMeasurement'),
            })
        
        # Text data points
        for name, data_point in device.get('textDataPoints', {}).items():
            sensors.append({
                'name': name,
                'type': 'text',
                'value': data_point.get('value'),
                'unit': data_point.get('unit'),
                'timestamp': data_point.get('timeStampUtcOfMeasurement'),
            })
        
        sensors_by_group[device_class] = sensors
    
    # Process top-level numberDataPoints and textDataPoints (Site Data)
    site_sensors = []
    for name, data_point in json_data.get('numberDataPoints', {}).items():
        site_sensors.append({
            'name': name,
            'type': 'number',
            'value': data_point.get('value'),
            'unit': data_point.get('unit'),
            'timestamp': data_point.get('timeStampUtcOfMeasurement'),
        })
    
    for name, data_point in json_data.get('textDataPoints', {}).items():
        site_sensors.append({
            'name': name,
            'type': 'text',
            'value': data_point.get('value'),
            'unit': data_point.get('unit'),
            'timestamp': data_point.get('timeStampUtcOfMeasurement'),
        })
    
    if site_sensors:
        sensors_by_group['Site Data'] = site_sensors
    
    # Process EnergyManagement
    for em in json_data.get('EnergyManagement', []):
        ref_device_id = em.get('referenceDeviceId', '')
        em_sensors = []
        
        for name, data_point in em.get('numberDataPoints', {}).items():
            em_sensors.append({
                'name': name,
                'type': 'number',
                'value': data_point.get('value'),
                'unit': data_point.get('unit'),
                'timestamp': data_point.get('timeStampUtcOfMeasurement'),
            })
        
        if em_sensors:
            # Add to Wallbox group (assuming energy management is for wallbox)
            if 'Wallbox' in sensors_by_group:
                sensors_by_group['Wallbox'].extend(em_sensors)
    
    return sensors_by_group


def convert_json_name_to_html_name(json_name: str, group: str) -> str:
    """
    Convert JSON sensor name to expected HTML parser name.
    
    Examples:
        'Energy.Battery.Charge.Level' -> 'Battery: Energy Battery Charge Level'
        'Power.AC.Phase.A' -> 'Inverter: Power AC Phase (A)'
        'LTE.RSSI' -> 'IoTEdgeDevice: LTE RSSI'
    """
    # Replace dots with spaces
    parts = json_name.split('.')
    
    # Handle special cases with letters in parentheses (Phase A/B/C, String 1/2)
    formatted_parts = []
    for i, part in enumerate(parts):
        # Check if this is a single letter or number that should be in parentheses
        if len(part) == 1 or (len(part) <= 2 and part.isdigit()):
            formatted_parts.append(f"({part})")
        else:
            formatted_parts.append(part)
    
    sensor_name = ' '.join(formatted_parts)
    
    # Use friendly_name to get consistent formatting
    return friendly_name(group, sensor_name)


def analyze_sensor_mapping(json_file: Path) -> None:
    """Analyze WebSocket JSON and compare with HTML parser names"""
    
    # Load JSON data
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    print("=" * 100)
    print("WebSocket JSON vs HTML Parser - Sensor Name Analysis")
    print("=" * 100)
    print()
    
    # Extract sensors by group
    sensors_by_group = extract_sensors_from_json(json_data)
    
    # Analyze each group
    total_sensors = 0
    for group, sensors in sorted(sensors_by_group.items()):
        print(f"\n{'─' * 100}")
        print(f"📦 {group} - {len(sensors)} sensors")
        print(f"{'─' * 100}\n")
        
        for sensor in sensors:
            json_name = sensor['name']
            html_name = convert_json_name_to_html_name(json_name, group)
            unique_id = make_id(html_name)
            
            # Format value
            value = sensor['value']
            unit = sensor.get('unit', 'None')
            if unit and unit != 'None':
                value_str = f"{value} {unit}"
            else:
                value_str = str(value)
            
            print(f"  JSON:  {json_name}")
            print(f"  HTML:  {html_name}")
            print(f"  ID:    {unique_id}")
            print(f"  Value: {value_str}")
            print(f"  Type:  {sensor['type']}")
            print()
            
            total_sensors += 1
    
    print("=" * 100)
    print(f"📊 Summary: {total_sensors} total sensors across {len(sensors_by_group)} device classes")
    print("=" * 100)
    print()
    
    # Group statistics
    print("\n📈 Sensors per Group:")
    for group in sorted(sensors_by_group.keys()):
        count = len(sensors_by_group[group])
        number_count = sum(1 for s in sensors_by_group[group] if s['type'] == 'number')
        text_count = sum(1 for s in sensors_by_group[group] if s['type'] == 'text')
        print(f"  {group:20s}: {count:3d} sensors ({number_count:3d} numeric, {text_count:2d} text)")
    
    # Check for naming patterns
    print("\n\n🔍 Naming Pattern Analysis:")
    print("─" * 100)
    
    # Analyze if JSON names match HTML parser expectations
    pattern_matches = {
        'Energy.*.Day': [],
        'Energy.*.Lifetime': [],
        'Power.*': [],
        'Voltage.*': [],
        'Current.*': [],
        'Temperature.*': [],
    }
    
    for group, sensors in sensors_by_group.items():
        for sensor in sensors:
            json_name = sensor['name']
            
            if '.Day' in json_name:
                pattern_matches['Energy.*.Day'].append((group, json_name))
            elif '.Lifetime' in json_name:
                pattern_matches['Energy.*.Lifetime'].append((group, json_name))
            elif json_name.startswith('Power.'):
                pattern_matches['Power.*'].append((group, json_name))
            elif json_name.startswith('Voltage.'):
                pattern_matches['Voltage.*'].append((group, json_name))
            elif json_name.startswith('Current.'):
                pattern_matches['Current.*'].append((group, json_name))
            elif json_name.startswith('Temperature.'):
                pattern_matches['Temperature.*'].append((group, json_name))
    
    for pattern, matches in pattern_matches.items():
        if matches:
            print(f"\n  {pattern}: {len(matches)} sensors")
            for group, name in matches[:5]:  # Show first 5
                print(f"    - {group}: {name}")
            if len(matches) > 5:
                print(f"    ... and {len(matches) - 5} more")
    
    print("\n" + "=" * 100)
    print("✅ Analysis complete!")
    print("=" * 100)


def main():
    json_file = Path("websocket_poc_data.json")
    
    if not json_file.exists():
        print(f"❌ Error: {json_file} not found")
        print("\nPlease run the WebSocket PoC test first:")
        print("  python test_websocket_poc.py <enpal_box_ip>")
        sys.exit(1)
    
    analyze_sensor_mapping(json_file)


if __name__ == "__main__":
    main()
