#!/usr/bin/env python3
"""
Proof of Concept Test for Enpal WebSocket Client

Usage:
    python test_websocket_poc.py <enpal_box_ip>
    
Example:
    python test_websocket_poc.py 192.168.1.100
"""
import asyncio
import sys
import json
import logging
import platform

# Add parent directory to path for imports
sys.path.insert(0, 'custom_components/enpal_webparser')

# Import directly from modules
from api.websocket_client import EnpalWebSocketClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def test_websocket_client(base_url: str):
    """Test WebSocket client with Enpal Box"""
    print(f"\n{'='*80}")
    print(f"Enpal WebSocket Client - Proof of Concept")
    print(f"{'='*80}\n")
    
    client = EnpalWebSocketClient(base_url)
    
    try:
        # 1. Connect
        print("[1/3] Connecting to Enpal Box...")
        success = await client.connect()
        
        if not success:
            print("❌ Connection failed!")
            return False
        
        print("✅ Connection established!\n")
        
        # 2. Fetch data
        print("[2/3] Fetching collector data...")
        data = await client.fetch_data()
        
        print("✅ Data received!\n")
        
        # 3. Display results
        print("[3/3] Parsing results...")
        print(f"\n{'='*80}")
        print("COLLECTOR DATA SUMMARY")
        print(f"{'='*80}\n")
        
        if isinstance(data, dict):
            # Collection info
            collection_id = data.get('collectionId', 'N/A')
            iot_device_id = data.get('ioTDeviceId', 'N/A')
            timestamp = data.get('timestampUtc', 'N/A')
            
            print(f"Collection ID:  {collection_id}")
            print(f"IoT Device ID:  {iot_device_id}")
            print(f"Timestamp:      {timestamp}\n")
            
            # Device collections
            device_collections = data.get('deviceCollections', [])
            print(f"Device Collections: {len(device_collections)}\n")
            
            for i, device in enumerate(device_collections, 1):
                device_class = device.get('deviceClass', 'Unknown')
                device_id = device.get('deviceId', 'N/A')
                
                print(f"  [{i}] {device_class}")
                print(f"      Device ID:  {device_id}")
                
                # Count data points
                num_points = device.get('numberDataPoints', {})
                text_points = device.get('textDataPoints', {})
                print(f"      Data Points: {len(num_points)} numeric, {len(text_points)} text")
                
                # Show first 3 data points as example
                if num_points:
                    print(f"      Sample Data:")
                    for key, value in list(num_points.items())[:3]:
                        point_value = value.get('value', 'N/A')
                        point_unit = value.get('unit', '')
                        print(f"        - {key}: {point_value} {point_unit}")
                
                print()
            
            # Energy management
            energy_mgmt = data.get('energyManagement', [])
            if energy_mgmt:
                print(f"Energy Management Entries: {len(energy_mgmt)}")
            
            # Error codes
            error_codes = data.get('errorCodes', [])
            if error_codes:
                print(f"⚠️  Error Codes: {len(error_codes)}")
                for error in error_codes[:3]:  # Show first 3
                    print(f"    - {error}")
            
            # Save full data to file
            output_file = "websocket_poc_data.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Full data saved to: {output_file}")
        
        else:
            print(f"⚠️  Unexpected data format: {type(data)}")
            print(f"Data: {data}")
        
        print(f"\n{'='*80}")
        print("✅ Proof of Concept SUCCESSFUL!")
        print(f"{'='*80}\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 4. Cleanup
        print("\n[Cleanup] Closing connection...")
        await client.close()
        print("✅ Connection closed\n")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_websocket_poc.py <enpal_box_ip>")
        print("\nExample:")
        print("  python test_websocket_poc.py 192.168.1.100")
        sys.exit(1)
    
    # Fix for Windows: Use SelectorEventLoop to avoid aiodns issues
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    ip_address = sys.argv[1]
    base_url = f"http://{ip_address}"
    
    # Run async test
    success = asyncio.run(test_websocket_client(base_url))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
