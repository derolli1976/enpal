#!/usr/bin/env python3
"""
Test Dual-Mode Integration

This script validates the integration changes:
1. Config Flow migration
2. Data source selection
3. Client factory in sensor.py
"""
import sys
from pathlib import Path

def test_config_flow_changes():
    """Test that config_flow.py has the necessary changes"""
    print("=" * 100)
    print("Testing Config Flow Changes")
    print("=" * 100)
    print()
    
    config_flow_file = Path("custom_components/enpal_webparser/config_flow.py")
    content = config_flow_file.read_text(encoding='utf-8')
    
    checks = {
        "detect_websocket_support function": "async def detect_websocket_support",
        "data_source in get_default_config": '"data_source"',
        "data_source in get_form_schema": 'vol.Optional("data_source"',
        "Auto-detect option": '"auto": "Auto-detect',
        "WebSocket option": '"websocket": "WebSocket',
        "HTML option": '"html": "HTML polling',
    }
    
    all_passed = True
    for check_name, check_string in checks.items():
        if check_string in content:
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name} - NOT FOUND")
            all_passed = False
    
    print()
    return all_passed


def test_sensor_platform_changes():
    """Test that sensor.py has the client factory"""
    print("=" * 100)
    print("Testing Sensor Platform Changes")
    print("=" * 100)
    print()
    
    sensor_file = Path("custom_components/enpal_webparser/sensor.py")
    content = sensor_file.read_text(encoding='utf-8')
    
    checks = {
        "Import EnpalApiClient": "from .api import",
        "data_source from config": 'data_source = entry.options.get("data_source"',
        "WebSocket client creation": "EnpalWebSocketClient(",
        "HTML client creation": "EnpalHtmlClient(",
        "Client connection check": "if not api_client.is_connected()",
        "fetch_data() call": "await api_client.fetch_data()",
        "api_client stored in coordinator": "coordinator.api_client = api_client",
    }
    
    all_passed = True
    for check_name, check_string in checks.items():
        if check_string in content:
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name} - NOT FOUND")
            all_passed = False
    
    print()
    return all_passed


def test_init_migration():
    """Test that __init__.py has migration logic"""
    print("=" * 100)
    print("Testing Migration Logic in __init__.py")
    print("=" * 100)
    print()
    
    init_file = Path("custom_components/enpal_webparser/__init__.py")
    content = init_file.read_text(encoding='utf-8')
    
    checks = {
        "Check for data_source": '"data_source" not in entry.options',
        "Migration message": "Migrating existing config",
        "Set data_source to html": '"data_source"] = "html"',
        "Update entry": "async_update_entry(entry, options=new_options)",
        "Close API client on unload": "await coordinator.api_client.close()",
    }
    
    all_passed = True
    for check_name, check_string in checks.items():
        if check_string in content:
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name} - NOT FOUND")
            all_passed = False
    
    print()
    return all_passed


def test_api_package():
    """Test that api package is properly set up"""
    print("=" * 100)
    print("Testing API Package Structure")
    print("=" * 100)
    print()
    
    api_dir = Path("custom_components/enpal_webparser/api")
    
    required_files = {
        "__init__.py": ["EnpalApiClient", "EnpalWebSocketClient", "EnpalHtmlClient"],
        "base.py": ["class EnpalApiClient(ABC)", "async def connect", "async def fetch_data"],
        "websocket_client.py": ["class EnpalWebSocketClient", "parse_websocket_json_to_sensors"],
        "websocket_parser.py": ["def parse_websocket_json_to_sensors"],
        "html_client.py": ["class EnpalHtmlClient", "parse_enpal_html_sensors"],
        "protocol.py": ["def encode_message", "def decode_messages"],
    }
    
    all_passed = True
    for filename, required_content in required_files.items():
        file_path = api_dir / filename
        
        if not file_path.exists():
            print(f"  ❌ {filename} - FILE NOT FOUND")
            all_passed = False
            continue
        
        content = file_path.read_text(encoding='utf-8')
        file_ok = True
        
        for required_string in required_content:
            if required_string not in content:
                file_ok = False
                break
        
        if file_ok:
            print(f"  ✅ {filename}")
        else:
            print(f"  ❌ {filename} - Missing required content")
            all_passed = False
    
    print()
    return all_passed


def main():
    """Run all tests"""
    print()
    print("╔" + "=" * 98 + "╗")
    print("║" + " " * 30 + "DUAL-MODE INTEGRATION TEST" + " " * 42 + "║")
    print("╚" + "=" * 98 + "╝")
    print()
    
    results = []
    
    # Test 1: Config Flow
    results.append(("Config Flow", test_config_flow_changes()))
    
    # Test 2: Sensor Platform
    results.append(("Sensor Platform", test_sensor_platform_changes()))
    
    # Test 3: Migration
    results.append(("Migration Logic", test_init_migration()))
    
    # Test 4: API Package
    results.append(("API Package", test_api_package()))
    
    # Summary
    print("=" * 100)
    print("TEST SUMMARY")
    print("=" * 100)
    print()
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name:30s}: {status}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        print("=" * 100)
        print("✅ ALL INTEGRATION TESTS PASSED!")
        print("=" * 100)
        print()
        print("The dual-mode integration is complete and ready for testing in Home Assistant.")
        print()
        print("Next steps:")
        print("  1. Copy integration to Home Assistant custom_components/")
        print("  2. Restart Home Assistant")
        print("  3. Test with existing config (should auto-migrate to HTML)")
        print("  4. Create new config and test WebSocket auto-detection")
        print("  5. Test manual WebSocket and HTML selection")
        print()
        return 0
    else:
        print("=" * 100)
        print("❌ SOME TESTS FAILED")
        print("=" * 100)
        print()
        print("Please review the failed tests above and fix the issues.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
