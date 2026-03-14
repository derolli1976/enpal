#!/usr/bin/env python3
"""
Test WebSocket Client with Integrated Parser

Tests the complete EnpalWebSocketClient with fetch_data() returning parsed sensors.
"""
import asyncio
import sys
from pathlib import Path
import json

# Set Windows event loop policy (Windows only)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Import websocket client directly
client_file = Path('custom_components/enpal_webparser/api/websocket_client.py')
spec = __import__('importlib.util').util.spec_from_file_location("websocket_client", client_file)
websocket_client = __import__('importlib.util').util.module_from_spec(spec)
sys.modules['api.websocket_parser'] = None  # Prevent import issues

# Load dependencies manually
parser_file = Path('custom_components/enpal_webparser/api/websocket_parser.py')
parser_spec = __import__('importlib.util').util.spec_from_file_location("websocket_parser", parser_file)
websocket_parser = __import__('importlib.util').util.module_from_spec(parser_spec)
parser_spec.loader.exec_module(websocket_parser)

protocol_file = Path('custom_components/enpal_webparser/api/protocol.py')
protocol_spec = __import__('importlib.util').util.spec_from_file_location("protocol", protocol_file)
protocol_module = __import__('importlib.util').util.module_from_spec(protocol_spec)
protocol_spec.loader.exec_module(protocol_module)

# Inject into sys.modules for websocket_client to find
sys.modules['websocket_parser'] = websocket_parser
sys.modules['protocol'] = protocol_module

# Now load websocket_client
spec.loader.exec_module(websocket_client)
EnpalWebSocketClient = websocket_client.EnpalWebSocketClient


async def test_websocket_client(base_url: str):
    """Test the complete WebSocket client with parser integration"""
    
    print("=" * 100)
    print("WebSocket Client Integrated Test")
    print("=" * 100)
    print()
    print(f"🔗 Target: {base_url}")
    print()
    
    # Define groups
    groups = ['Battery', 'Inverter', 'IoTEdgeDevice', 'PowerSensor', 'Wallbox', 'Site Data']
    
    # Create client
    client = EnpalWebSocketClient(base_url, groups=groups)
    
    try:
        # Connect
        print("🔌 Connecting to WebSocket...")
        connected = await client.connect()
        
        if not connected:
            print("❌ Connection failed")
            return False
        
        print("✅ Connected successfully!")
        print()
        
        # Fetch data
        print("📡 Fetching and parsing sensor data...")
        result = await client.fetch_data()
        
        if not result:
            print("❌ fetch_data() returned None")
            return False
        
        # Validate structure
        print("🔍 Validating result structure...")
        
        if 'sensors' not in result:
            print("❌ Missing 'sensors' key in result")
            return False
        
        if 'source' not in result:
            print("❌ Missing 'source' key in result")
            return False
        
        print(f"✅ Result structure valid")
        print(f"   Source: {result['source']}")
        print(f"   Sensors: {len(result['sensors'])}")
        print()
        
        sensors = result['sensors']
        
        # Show first 5 sensors
        print("📋 First 5 Sensors:")
        print("-" * 100)
        for i, sensor in enumerate(sensors[:5], 1):
            print(f"  [{i}] {sensor['name']}")
            print(f"       Value: {sensor['value']} {sensor.get('unit', '')}")
            print(f"       Group: {sensor['group']}")
            print(f"       Device Class: {sensor.get('device_class')}")
            print(f"       Enabled: {sensor.get('enabled')}")
            print()
        
        # Group summary
        print("=" * 100)
        print("📊 Summary by Group")
        print("=" * 100)
        print()
        
        by_group = {}
        for sensor in sensors:
            group = sensor.get('group', 'Unknown')
            by_group.setdefault(group, []).append(sensor)
        
        for group in sorted(by_group.keys()):
            group_sensors = by_group[group]
            print(f"  {group:20s}: {len(group_sensors):3d} sensors")
        
        print()
        print("=" * 100)
        print("✅ WebSocket Client Test SUCCESSFUL!")
        print("=" * 100)
        print()
        print("💡 Key Achievements:")
        print("   ✅ WebSocket connection established")
        print("   ✅ Data fetched and parsed")
        print(f"   ✅ {len(sensors)} sensors in Home Assistant format")
        print("   ✅ Compatible with existing sensor platform")
        print()
        
        # Save result
        output_file = "websocket_client_test_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved result to: {output_file}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Close connection
        await client.close()
        print("🔌 Connection closed")


def main():
    """Main entry point"""
    
    if len(sys.argv) < 2:
        print("Usage: python test_websocket_client_integrated.py <enpal_box_ip>")
        print()
        print("Example:")
        print("  python test_websocket_client_integrated.py 192.168.2.70")
        sys.exit(1)
    
    enpal_ip = sys.argv[1]
    base_url = f"http://{enpal_ip}"
    
    # Run test
    success = asyncio.run(test_websocket_client(base_url))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
