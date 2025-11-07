"""
Test for Heatpump sensor group support.
"""
from custom_components.enpal_webparser.utils import parse_enpal_html_sensors
from custom_components.enpal_webparser.const import DEFAULT_GROUPS


def test_heatpump_group_in_default_groups():
    """Test that Heatpump is included in DEFAULT_GROUPS."""
    assert "Heatpump" in DEFAULT_GROUPS, "Heatpump should be in DEFAULT_GROUPS"
    print("✓ Heatpump is included in DEFAULT_GROUPS")


def test_parse_heatpump_sensors():
    """Test parsing of Heatpump sensor group from HTML."""
    # Minimal HTML with Heatpump group
    html = """
    <!DOCTYPE html>
    <html>
    <body>
        <div class="card mb-4">
            <div class="card-header"><h2>Heatpump</h2></div>
            <div class="card-body">
                <table class="table table-bordered table-striped">
                    <thead>
                        <tr>
                            <th class="col-3">Sensor Name</th>
                            <th class="col-3">Value</th>
                            <th class="col-3">Timestamp</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Heatpump.DomesticHotWater.Temperature</td>
                            <td>51°C</td>
                            <td>11/07/2025 18:05:16</td>
                        </tr>
                        <tr>
                            <td>Heatpump.Energy.Consumption.Total.Lifetime</td>
                            <td>1031kWh</td>
                            <td>11/07/2025 18:05:16</td>
                        </tr>
                        <tr>
                            <td>Heatpump.Operation.Mode.Midea</td>
                            <td>3</td>
                            <td>11/07/2025 18:05:16</td>
                        </tr>
                        <tr>
                            <td>Heatpump.Outside.Temperature</td>
                            <td>10°C</td>
                            <td>11/07/2025 18:05:16</td>
                        </tr>
                        <tr>
                            <td>Heatpump.Power.Consumption.Total</td>
                            <td>0.02kW</td>
                            <td>11/07/2025 18:05:16</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Parse with Heatpump group
    sensors = parse_enpal_html_sensors(html, groups=["Heatpump"])
    
    # Verify sensors were found
    assert len(sensors) > 0, "Should find Heatpump sensors"
    
    # Check sensor names
    sensor_names = [s['name'] for s in sensors]
    assert any("DomesticHotWater" in name for name in sensor_names), "Should find DomesticHotWater Temperature sensor"
    assert any("Energy" in name and "Consumption" in name for name in sensor_names), "Should find Energy Consumption sensor"
    assert any("Operation" in name and "Mode" in name for name in sensor_names), "Should find Operation Mode sensor"
    assert any("Outside" in name and "Temperature" in name for name in sensor_names), "Should find Outside Temperature sensor"
    assert any("Power" in name and "Consumption" in name for name in sensor_names), "Should find Power Consumption sensor"
    
    # Verify group is correct
    for sensor in sensors:
        assert sensor['group'] == 'Heatpump', f"Sensor {sensor['name']} should be in Heatpump group"
    
    print(f"✓ Successfully parsed {len(sensors)} Heatpump sensors:")
    for sensor in sensors:
        print(f"  - {sensor['name']} = {sensor['value']}")


def test_heatpump_sensors_not_parsed_when_group_not_selected():
    """Test that Heatpump sensors are ignored when group is not selected."""
    html = """
    <!DOCTYPE html>
    <html>
    <body>
        <div class="card mb-4">
            <div class="card-header"><h2>Heatpump</h2></div>
            <div class="card-body">
                <table class="table table-bordered table-striped">
                    <tbody>
                        <tr>
                            <td>Heatpump.Power.Consumption.Total</td>
                            <td>0.02kW</td>
                            <td>11/07/2025 18:05:16</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Parse WITHOUT Heatpump group
    sensors = parse_enpal_html_sensors(html, groups=["Battery", "Inverter"])
    
    # Should find no sensors
    assert len(sensors) == 0, "Should not find Heatpump sensors when group not selected"
    print("✓ Heatpump sensors correctly ignored when group not selected")


if __name__ == "__main__":
    # Run tests directly
    print("=" * 80)
    print("Testing Heatpump sensor group support")
    print("=" * 80)
    
    try:
        test_heatpump_group_in_default_groups()
        test_parse_heatpump_sensors()
        test_heatpump_sensors_not_parsed_when_group_not_selected()
        print("\n" + "=" * 80)
        print("All Heatpump tests PASSED ✓")
        print("=" * 80)
    except AssertionError as e:
        print(f"\n✗ Test FAILED: {e}")
        import sys
        sys.exit(1)
