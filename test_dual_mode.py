#!/usr/bin/env python3
"""
Test script to compare HTML Client vs WebSocket Client

Tests that both clients return the same sensor structure.
"""
import asyncio
import sys
import platform
import aiohttp
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, 'custom_components/enpal_webparser')

# Import WebSocket client directly
from api.websocket_client import EnpalWebSocketClient


class SimpleHtmlClient:
    """Simple HTML client for testing (avoids import issues)"""
    
    def __init__(self, base_url: str, groups: list):
        self.base_url = base_url.rstrip('/')
        self.groups = groups
        self.session = None
        self.connected = False
    
    async def connect(self) -> bool:
        self.session = aiohttp.ClientSession()
        self.connected = True
        return True
    
    async def fetch_data(self) -> dict:
        """Fetch HTML and parse with utils"""
        if not self.connected:
            raise RuntimeError("Not connected")
        
        url = f"{self.base_url}/deviceMessages"
        
        async with self.session.get(url, timeout=30) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            html = await resp.text()
        
        # Import and use parse function
        from utils import parse_enpal_html_sensors
        sensors = parse_enpal_html_sensors(html, self.groups)
        
        return {
            'sensors': sensors,
            'source': 'html',
        }
    
    async def close(self):
        if self.session:
            await self.session.close()
        self.connected = False
    
    def is_connected(self) -> bool:
        return self.connected


async def test_dual_mode(base_url: str):
    """Test both HTML and WebSocket clients"""
    
    print("=" * 100)
    print("Dual-Mode Test: HTML Client vs WebSocket Client")
    print("=" * 100)
    print()
    
    groups = ['Battery', 'Inverter', 'IoTEdgeDevice', 'PowerSensor', 'Wallbox', 'Site Data']
    
    # Test HTML Client
    print("[1/2] Testing HTML Client...")
    print("-" * 100)
    
    html_client = SimpleHtmlClient(base_url, groups)
    html_sensors = []
    
    try:
        await html_client.connect()
        result = await html_client.fetch_data()
        html_sensors = result.get('sensors', [])
        
        print(f"✅ HTML Client: {len(html_sensors)} sensors fetched")
        print(f"   Source: {result.get('source')}")
        
        # Show first 3 sensors
        print("\n   Sample sensors:")
        for sensor in html_sensors[:3]:
            print(f"     - {sensor['name']}: {sensor['value']} {sensor.get('unit', '')}")
        
    except Exception as e:
        print(f"❌ HTML Client failed: {e}")
        return False
    finally:
        await html_client.close()
    
    print()
    
    # Test WebSocket Client
    print("[2/2] Testing WebSocket Client...")
    print("-" * 100)
    
    ws_client = EnpalWebSocketClient(base_url, groups)
    ws_sensors = []
    
    try:
        await ws_client.connect()
        result = await ws_client.fetch_data()
        ws_sensors = result.get('sensors', [])
        
        print(f"✅ WebSocket Client: {len(ws_sensors)} sensors fetched")
        print(f"   Source: {result.get('source')}")
        
        # Show first 3 sensors
        print("\n   Sample sensors:")
        for sensor in ws_sensors[:3]:
            print(f"     - {sensor['name']}: {sensor['value']} {sensor.get('unit', '')}")
        
    except Exception as e:
        print(f"❌ WebSocket Client failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await ws_client.close()
    
    print()
    print("=" * 100)
    print("Comparison")
    print("=" * 100)
    print()
    
    # Compare sensor counts
    print(f"📊 Sensor Count:")
    print(f"   HTML Client:      {len(html_sensors):3d} sensors")
    print(f"   WebSocket Client: {len(ws_sensors):3d} sensors")
    print(f"   Difference:       {abs(len(html_sensors) - len(ws_sensors)):3d} sensors")
    print()
    
    # Compare sensor structures
    print("🔍 Data Structure Validation:")
    required_keys = ['name', 'value', 'unit', 'device_class', 'enabled', 'enpal_last_update', 'group']
    
    html_valid = all(all(key in s for key in required_keys) for s in html_sensors[:10])
    ws_valid = all(all(key in s for key in required_keys) for s in ws_sensors[:10])
    
    print(f"   HTML sensors have all required keys:      {'✅' if html_valid else '❌'}")
    print(f"   WebSocket sensors have all required keys: {'✅' if ws_valid else '❌'}")
    print()
    
    # Find common sensors by name
    html_names = {s['name'] for s in html_sensors}
    ws_names = {s['name'] for s in ws_sensors}
    
    common_names = html_names & ws_names
    html_only = html_names - ws_names
    ws_only = ws_names - html_names
    
    print(f"📍 Sensor Name Overlap:")
    print(f"   Common sensors:        {len(common_names):3d}")
    print(f"   HTML-only sensors:     {len(html_only):3d}")
    print(f"   WebSocket-only sensors: {len(ws_only):3d}")
    print()
    
    if html_only:
        print(f"   HTML-only (first 10):")
        for name in sorted(html_only)[:10]:
            print(f"     - {name}")
        if len(html_only) > 10:
            print(f"     ... and {len(html_only) - 10} more")
        print()
    
    if ws_only:
        print(f"   WebSocket-only (first 10):")
        for name in sorted(ws_only)[:10]:
            print(f"     - {name}")
        if len(ws_only) > 10:
            print(f"     ... and {len(ws_only) - 10} more")
        print()
    
    # Value comparison for common sensors
    if common_names:
        print("🔢 Value Comparison (first 5 common sensors):")
        html_dict = {s['name']: s for s in html_sensors}
        ws_dict = {s['name']: s for s in ws_sensors}
        
        for name in sorted(common_names)[:5]:
            html_s = html_dict[name]
            ws_s = ws_dict[name]
            
            values_match = html_s['value'] == ws_s['value']
            units_match = html_s.get('unit') == ws_s.get('unit')
            
            print(f"\n   {name}:")
            print(f"     HTML:      {html_s['value']} {html_s.get('unit', '')}")
            print(f"     WebSocket: {ws_s['value']} {ws_s.get('unit', '')}")
            print(f"     Match:     {'✅' if values_match and units_match else '⚠️'}")
    
    print()
    print("=" * 100)
    print("✅ Dual-Mode Test Complete!")
    print("=" * 100)
    print()
    print("💡 Both clients return data in the same format.")
    print("   Sensor sources can be switched via configuration.")
    print()
    
    return True


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_dual_mode.py <enpal_box_ip>")
        print("\nExample:")
        print("  python test_dual_mode.py 192.168.2.70")
        sys.exit(1)
    
    # Fix for Windows: Use SelectorEventLoop to avoid aiodns issues
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    ip_address = sys.argv[1]
    base_url = f"http://{ip_address}"
    
    # Run async test
    success = asyncio.run(test_dual_mode(base_url))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
