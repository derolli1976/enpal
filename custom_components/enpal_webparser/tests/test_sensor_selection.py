"""
Unit tests for CumulativeEnergySensor DC power sensor selection logic.

Tests the three-tier fallback system:
1. Explicit candidate list (known sensors)
2. Pattern matching (inverter_power_dc_total*)
3. Fallback with logging
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.enpal_webparser.sensor import CumulativeEnergySensor
from custom_components.enpal_webparser.utils import make_id


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {
        "enpal_webparser": {
            "cumulative_energy_state": {
                "value": 0.0,
                "last_updated": "2024-01-01T00:00:00"
            }
        }
    }
    return hass


@pytest.fixture
def mock_coordinator(mock_hass):
    """Create a mock DataUpdateCoordinator."""
    coordinator = Mock(spec=DataUpdateCoordinator)
    coordinator.data = []
    coordinator.async_add_listener = Mock()
    return coordinator


def create_sensor_with_mocked_state(mock_hass, mock_coordinator, sensor_names, interval=60):
    """Helper to create a sensor with async_write_ha_state mocked."""
    sensor = CumulativeEnergySensor(mock_hass, mock_coordinator, sensor_names, interval)
    sensor.async_write_ha_state = Mock()
    return sensor


class TestCumulativeEnergySensorSelection:
    """Test sensor selection logic for different inverter types."""
    
    def test_huawei_sensor_selection(self, mock_hass, mock_coordinator):
        """Test that Huawei sensor is selected when available (Priority 1)."""
        mock_coordinator.data = [
            {"name": "Inverter: Power DC Total (Huawei)", "value": "5000", "timestamp": "01/01/2024 12:00:00"},
            {"name": "Inverter: Power AC", "value": "4800", "timestamp": "01/01/2024 12:00:00"},
        ]
        
        sensor = create_sensor_with_mocked_state(
            mock_hass, mock_coordinator, ["Inverter: Power DC Total (Huawei)"]
        )
        
        # Trigger update to determine active source
        sensor._handle_coordinator_update()
        
        # Should select Huawei sensor
        assert sensor._active_source_uid == make_id("Inverter: Power DC Total (Huawei)")
        assert sensor._active_source_uid == "inverter_power_dc_total_huawei"
    
    def test_calculated_sensor_as_last_resort(self, mock_hass, mock_coordinator):
        """Test that calculated sensor is ONLY used as absolute last resort (Priority 4).
        
        Calculated sensor should only be used when no other options exist.
        """
        mock_coordinator.data = [
            {"name": "Inverter: Power DC Total Calculated", "value": "5000", "timestamp": "01/01/2024 12:00:00"},
            {"name": "Inverter: Power AC", "value": "4800", "timestamp": "01/01/2024 12:00:00"},
        ]
        
        sensor = create_sensor_with_mocked_state(
            mock_hass, mock_coordinator, ["Inverter: Power DC Total Calculated"]
        )
        sensor._handle_coordinator_update()
        
        # Should select calculated sensor (only available DC power sensor)
        assert sensor._active_source_uid == "inverter_power_dc_total_calculated"
    
    def test_generic_sensor_selection(self, mock_hass, mock_coordinator):
        """Test that generic sensor is selected when Huawei not available (Priority 2)."""
        mock_coordinator.data = [
            {"name": "Inverter: Power DC Total", "value": "5000", "timestamp": "01/01/2024 12:00:00"},
            {"name": "Inverter: Power AC", "value": "4800", "timestamp": "01/01/2024 12:00:00"},
        ]
        
        sensor_names = [
            "Inverter: Power DC Total (Huawei)",
            "Inverter: Power DC Total",
            "Inverter: Power DC Total Calculated",
        ]
        sensor = create_sensor_with_mocked_state(mock_hass, mock_coordinator, sensor_names)
        sensor._handle_coordinator_update()
        
        # Should select generic sensor (higher priority than calculated)
        assert sensor._active_source_uid == "inverter_power_dc_total"
    
    def test_pattern_matching_unknown_sensor(self, mock_hass, mock_coordinator):
        """Test that manufacturer-specific sensors are found (Priority 2).
        
        Tests the cascade: Huawei → Manufacturer-specific (SMA, Fronius) → Generic → Calculated
        This verifies manufacturer-specific sensors are detected and prioritized.
        """
        mock_coordinator.data = [
            {"name": "Inverter: Power DC Total (SMA)", "value": "5000", "timestamp": "01/01/2024 12:00:00"},
            {"name": "Inverter: Power AC", "value": "4800", "timestamp": "01/01/2024 12:00:00"},
        ]
        
        # Simulate the setup code finding the sensor and passing it to the sensor class
        sensor = create_sensor_with_mocked_state(
            mock_hass, 
            mock_coordinator, 
            ["Inverter: Power DC Total (SMA)"]  # Manufacturer-specific result from setup
        )
        sensor._handle_coordinator_update()
        
        # Should use the manufacturer-specific sensor
        assert sensor._active_source_uid == "inverter_power_dc_total_sma"
    
    def test_no_matching_sensor_fallback(self, mock_hass, mock_coordinator):
        """Test fallback behavior when no suitable sensor found."""
        mock_coordinator.data = [
            {"name": "Inverter: Power AC", "value": "4800", "timestamp": "01/01/2024 12:00:00"},
            {"name": "Battery: Power", "value": "1000", "timestamp": "01/01/2024 12:00:00"},
        ]
        
        sensor_names = [
            "Inverter: Power DC Total (Huawei)",
            "Inverter: Power DC Total",
            "Inverter: Power DC Total Calculated",
        ]
        
        with patch('custom_components.enpal_webparser.sensor._LOGGER') as mock_logger:
            sensor = create_sensor_with_mocked_state(mock_hass, mock_coordinator, sensor_names)
            sensor._handle_coordinator_update()
            
            # Should remain None (no sensor found)
            assert sensor._active_source_uid is None
            
            # Should have logged warning
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "No suitable DC power sensor found" in warning_msg
    
    def test_energy_calculation_with_selected_sensor(self, mock_hass, mock_coordinator):
        """Test that energy calculation works with auto-selected sensor."""
        mock_coordinator.data = [
            {"name": "Inverter: Power DC Total (Huawei)", "value": "5000", "timestamp": "01/01/2024 12:00:00"},
        ]
        
        sensor = create_sensor_with_mocked_state(
            mock_hass, mock_coordinator, ["Inverter: Power DC Total (Huawei)"], 3600
        )
        sensor._value = 0.0
        
        # First update - selects sensor and calculates
        sensor._handle_coordinator_update()
        
        # Should have calculated energy: 5000W * 1h / 1000 = 5 kWh
        assert sensor._active_source_uid == "inverter_power_dc_total_huawei"
        assert sensor._value == pytest.approx(5.0, rel=0.01)
        
        # Second update with different power
        mock_coordinator.data = [
            {"name": "Inverter: Power DC Total (Huawei)", "value": "3000", "timestamp": "01/01/2024 13:00:00"},
        ]
        sensor._handle_coordinator_update()
        
        # Should add: 5 + 3 = 8 kWh
        assert sensor._value == pytest.approx(8.0, rel=0.01)
    
    def test_pattern_does_not_match_wrong_sensors(self, mock_hass, mock_coordinator):
        """Test that pattern matching is specific and doesn't match wrong sensors."""
        mock_coordinator.data = [
            {"name": "Inverter: Power AC", "value": "4800", "timestamp": "01/01/2024 12:00:00"},
            {"name": "Battery: Power DC", "value": "1000", "timestamp": "01/01/2024 12:00:00"},
            {"name": "Inverter: Power Reactive", "value": "100", "timestamp": "01/01/2024 12:00:00"},
        ]
        
        sensor_names = [
            "Inverter: Power DC Total (Huawei)",
            "Inverter: Power DC Total",
            "Inverter: Power DC Total Calculated",
        ]
        
        with patch('custom_components.enpal_webparser.sensor._LOGGER') as mock_logger:
            sensor = create_sensor_with_mocked_state(mock_hass, mock_coordinator, sensor_names)
            sensor._handle_coordinator_update()
            
            # Should NOT match any of these wrong sensors
            assert sensor._active_source_uid is None
            mock_logger.warning.assert_called_once()
    
    def test_multiple_matching_sensors_first_wins(self, mock_hass, mock_coordinator):
        """Test that first matching sensor in priority order is selected.
        
        Priority order: 
        1. Huawei (highest) 
        2. Generic 
        3. Calculated (lowest - least accurate)
        """
        mock_coordinator.data = [
            {"name": "Inverter: Power DC Total", "value": "5000", "timestamp": "01/01/2024 12:00:00"},
            {"name": "Inverter: Power DC Total (Huawei)", "value": "5100", "timestamp": "01/01/2024 12:00:00"},
            {"name": "Inverter: Power DC Total Calculated", "value": "4900", "timestamp": "01/01/2024 12:00:00"},
        ]
        
        sensor_names = [
            "Inverter: Power DC Total (Huawei)",
            "Inverter: Power DC Total",
            "Inverter: Power DC Total Calculated",
        ]
        sensor = create_sensor_with_mocked_state(mock_hass, mock_coordinator, sensor_names)
        sensor._handle_coordinator_update()
        
        # Should select Huawei (highest priority)
        assert sensor._active_source_uid == "inverter_power_dc_total_huawei"
    
    def test_generic_preferred_over_calculated(self, mock_hass, mock_coordinator):
        """Test that generic sensor is preferred over calculated (Priority 3 vs 4).
        
        When both generic and calculated are available, generic should win.
        """
        mock_coordinator.data = [
            {"name": "Inverter: Power DC Total", "value": "5000", "timestamp": "01/01/2024 12:00:00"},
            {"name": "Inverter: Power DC Total Calculated", "value": "4900", "timestamp": "01/01/2024 12:00:00"},
            {"name": "Inverter: Power AC", "value": "4800", "timestamp": "01/01/2024 12:00:00"},
        ]
        
        sensor = create_sensor_with_mocked_state(
            mock_hass, mock_coordinator, ["Inverter: Power DC Total"]
        )
        sensor._handle_coordinator_update()
        
        # Should select generic over calculated (higher priority, direct measurement)
        assert sensor._active_source_uid == "inverter_power_dc_total"
    
    def test_manufacturer_specific_preferred_over_generic(self, mock_hass, mock_coordinator):
        """Test that manufacturer-specific sensor is preferred over generic (Priority 2 vs 3).
        
        When both manufacturer-specific (e.g., Fronius) and generic are available,
        manufacturer-specific should win.
        """
        mock_coordinator.data = [
            {"name": "Inverter: Power DC Total (Fronius)", "value": "5000", "timestamp": "01/01/2024 12:00:00"},
            {"name": "Inverter: Power DC Total", "value": "4900", "timestamp": "01/01/2024 12:00:00"},
            {"name": "Inverter: Power AC", "value": "4800", "timestamp": "01/01/2024 12:00:00"},
        ]
        
        sensor = create_sensor_with_mocked_state(
            mock_hass, mock_coordinator, ["Inverter: Power DC Total (Fronius)"]
        )
        sensor._handle_coordinator_update()
        
        # Should select manufacturer-specific over generic
        assert sensor._active_source_uid == "inverter_power_dc_total_fronius"
    
    def test_sensor_selection_persistence(self, mock_hass, mock_coordinator):
        """Test that sensor selection persists across updates."""
        mock_coordinator.data = [
            {"name": "Inverter: Power DC Total (Huawei)", "value": "5000", "timestamp": "01/01/2024 12:00:00"},
        ]
        
        sensor = create_sensor_with_mocked_state(
            mock_hass, mock_coordinator, ["Inverter: Power DC Total (Huawei)"]
        )
        sensor._value = 0.0
        
        # First update
        sensor._handle_coordinator_update()
        selected_sensor = sensor._active_source_uid
        
        # Second update - should use same sensor
        mock_coordinator.data = [
            {"name": "Inverter: Power DC Total (Huawei)", "value": "6000", "timestamp": "01/01/2024 12:01:00"},
        ]
        sensor._handle_coordinator_update()
        
        # Should still use same sensor (not re-detect)
        assert sensor._active_source_uid == selected_sensor
    
    def test_extra_state_attributes_shows_source(self, mock_hass, mock_coordinator):
        """Test that extra_state_attributes shows which sensor is used."""
        mock_coordinator.data = [
            {"name": "Inverter: Power DC Total Calculated", "value": "5000", "timestamp": "01/01/2024 12:00:00"},
        ]
        
        sensor = create_sensor_with_mocked_state(
            mock_hass, mock_coordinator, ["Inverter: Power DC Total Calculated"]
        )
        
        # Before update - not determined
        attrs = sensor.extra_state_attributes
        assert attrs["source_sensor"] == "Not determined"
        
        # After update - shows selected sensor
        sensor._handle_coordinator_update()
        attrs = sensor.extra_state_attributes
        assert attrs["source_sensor"] == "inverter_power_dc_total_calculated"
    
    def test_make_id_consistency(self, mock_hass, mock_coordinator):
        """Test that make_id transformation is consistent."""
        from custom_components.enpal_webparser.utils import make_id
        
        # Test various sensor names
        assert make_id("Inverter: Power DC Total (Huawei)") == "inverter_power_dc_total_huawei"
        assert make_id("Inverter: Power DC Total Calculated") == "inverter_power_dc_total_calculated"
        assert make_id("Inverter: Power DC Total") == "inverter_power_dc_total"
        assert make_id("Inverter: Power DC Total SMA") == "inverter_power_dc_total_sma"
        
        # Verify sensor uses same transformation
        mock_coordinator.data = [
            {"name": "Inverter: Power DC Total (Huawei)", "value": "5000", "timestamp": "01/01/2024 12:00:00"},
        ]
        
        sensor = create_sensor_with_mocked_state(
            mock_hass, mock_coordinator, ["Inverter: Power DC Total (Huawei)"]
        )
        sensor._handle_coordinator_update()
        
        # Should match make_id output
        assert sensor._active_source_uid == make_id("Inverter: Power DC Total (Huawei)")
