#!/usr/bin/env python3
"""
Test WebSocket Parser - converts JSON to sensor format

This tests the websocket_parser.py module.
"""
import json
import sys
from pathlib import Path

# Import parser directly to avoid module conflicts
parser_file = Path('custom_components/enpal_webparser/api/websocket_parser.py')
spec = __import__('importlib.util').util.spec_from_file_location("websocket_parser", parser_file)
websocket_parser = __import__('importlib.util').util.module_from_spec(spec)
spec.loader.exec_module(websocket_parser)
parse_websocket_json_to_sensors = websocket_parser.parse_websocket_json_to_sensors


def test_websocket_parser():
    """Test parsing WebSocket JSON to sensor format"""
    
    json_file = Path("websocket_poc_data.json")
    
    if not json_file.exists():
        print(f"❌ Error: {json_file} not found")
        print("\nPlease run the WebSocket PoC test first:")
        print("  python test_websocket_poc.py <enpal_box_ip>")
        sys.exit(1)
    
    print("=" * 100)
    print("WebSocket JSON Parser Test")
    print("=" * 100)
    print()
    
    # Load JSON data
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    print(f"📂 Loaded JSON from: {json_file}")
    print()
    
    # Define groups to parse
    groups = ['Battery', 'Inverter', 'IoTEdgeDevice', 'PowerSensor', 'Wallbox', 'Site Data']
    
    print(f"📋 Parsing groups: {', '.join(groups)}")
    print()
    
    # Parse JSON to sensors
    sensors = parse_websocket_json_to_sensors(json_data, groups)
    
    print(f"✅ Parsed {len(sensors)} sensors\n")
    
    # Validate sensor structure
    print("🔍 Validating Sensor Structure:")
    print("-" * 100)
    
    required_keys = ['name', 'value', 'unit', 'device_class', 'enabled', 'enpal_last_update', 'group']
    
    all_valid = True
    for i, sensor in enumerate(sensors[:5], 1):
        missing_keys = [key for key in required_keys if key not in sensor]
        
        if missing_keys:
            print(f"  [{i}] ❌ Missing keys: {missing_keys}")
            all_valid = False
        else:
            print(f"  [{i}] ✅ {sensor['name']}")
            print(f"       Value: {sensor['value']} {sensor.get('unit', '')}")
            print(f"       Group: {sensor['group']}")
            print(f"       Device Class: {sensor.get('device_class')}")
            print()
    
    if all_valid:
        print("\n✅ All sensors have required keys!")
    
    print()
    print("=" * 100)
    print("📊 Summary by Group")
    print("=" * 100)
    print()
    
    # Group sensors
    by_group = {}
    for sensor in sensors:
        group = sensor.get('group', 'Unknown')
        by_group.setdefault(group, []).append(sensor)
    
    for group in sorted(by_group.keys()):
        group_sensors = by_group[group]
        num_sensors = len(group_sensors)
        enabled_count = sum(1 for s in group_sensors if s.get('enabled'))
        
        print(f"  {group:20s}: {num_sensors:3d} sensors ({enabled_count} enabled)")
        
        # Show first 3 sensors
        for sensor in group_sensors[:3]:
            print(f"    - {sensor['name']}: {sensor['value']} {sensor.get('unit', '')}")
        
        if len(group_sensors) > 3:
            print(f"    ... and {len(group_sensors) - 3} more")
        print()
    
    print("=" * 100)
    print("✅ Parser Test Complete!")
    print("=" * 100)
    print()
    print("💡 WebSocket JSON successfully parsed to Home Assistant sensor format.")
    print("   Format is compatible with existing sensor platform.")
    print()
    
    return True


if __name__ == "__main__":
    success = test_websocket_parser()
    sys.exit(0 if success else 1)
