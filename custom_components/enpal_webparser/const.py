#
# Home Assistant Custom Component: Enpal Webparser
#
# File: const.py
#
# Description:
#   Shared constants for the Enpal Webparser integration.
#   Stores domain, default URLs, groups, unit mappings, and wallbox settings.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
# Repository:   https://github.com/derolli1976/enpal
#
# Compatible with Home Assistant Core 2024.x and later.
#
# See README.md for setup and usage instructions.
#

# --- Domain & Integration Info ---
DOMAIN = "enpal_webparser"

# --- Default Connection Settings ---
# Note: Enpal boxes get IP via DHCP, use auto-discovery or check your router
DEFAULT_URL = "http://192.168.1.1/deviceMessages"  # Placeholder - use discovery or check router
DEFAULT_INTERVAL = 60

DEFAULT_GROUPS = [
    "Wallbox",
    "Battery",
    "Inverter",
    "Site Data",
    "IoTEdgeDevice",
    "PowerSensor",
    "Heatpump",
]

DEFAULT_USE_WALLBOX_ADDON = False
DEFAULT_WALLBOX_API_ENDPOINT = "http://localhost:36725/wallbox"

# --- Device Class/Unit Mappings ---
DEFAULT_UNITS = {
    "power": "W",
    "energy": "kWh",
    "voltage": "V",
    "current": "A",
    "temperature": "°C",
    "frequency": "Hz",
}

UNIT_DEVICE_CLASS_MAP = {
    "kWh": "energy",
    "Wh": "energy",
    "kW": "power",
    "W": "power",
    "V": "voltage",
    "A": "current",
    "Hz": "frequency",
    "°C": "temperature",
    "%": None,
}

DEVICE_CLASS_OVERRIDES = {
    "energy_battery_charge_level": "battery",
    "energy_battery_charge_level_unit_1": "battery",
    "energy_battery_charge_level_unit_2": "battery",
    "energy_battery_charge_level_absolute": "battery",
    "energy_battery_charge_load": "energy_storage",
}

STATE_CLASS_OVERRIDES = {
    "energy_battery_charge_level": "measurement",
    "energy_battery_charge_level_unit_1": "measurement",
    "energy_battery_charge_level_unit_2": "measurement",
    "energy_battery_charge_level_absolute": "measurement",
    "energy_battery_charge_load": "measurement",
}

# --- Wallbox Mode Mapping ---
WALLBOX_MODE_MAP = {
    "eco": "Eco",
    "fast": "Full",
    "solar": "Solar",
}

# --- Date/Time Formats ---
ENPAL_TIMESTAMP_FORMAT = "%m/%d/%Y %H:%M:%S"

ICON_MAP = {
    # IoT Edge Device
    "iotedgedevice_cpu_load": "mdi:cpu-64-bit",
    "iotedgedevice_hw_cronny_result": "mdi:cog-sync",
    "iotedgedevice_iot_data_consumption_lan_down_month": "mdi:download-network-outline",
    "iotedgedevice_iot_data_consumption_lan_up_month": "mdi:upload-network-outline",
    "iotedgedevice_iot_data_consumption_lte_down_month": "mdi:download-network",
    "iotedgedevice_iot_data_consumption_lte_up_month": "mdi:upload-network",
    "iotedgedevice_iot_mainstate": "mdi:state-machine",
    "iotedgedevice_lte_cellularguard_result_timestamp": "mdi:calendar-clock",
    "iotedgedevice_lte_cellularguard_result_value": "mdi:cellphone-cog",
    "iotedgedevice_lte_cellularguard_result_version": "mdi:cellphone-cog",
    "iotedgedevice_lte_connection_type": "mdi:access-point",
    "iotedgedevice_lte_cronny_result": "mdi:cellphone-cog",
    "iotedgedevice_lte_fail_over_message_0": "mdi:alert-circle-outline",
    "iotedgedevice_lte_fail_over_message_1": "mdi:alert-circle-outline",
    "iotedgedevice_lte_fail_over_message_2": "mdi:alert-circle-outline",
    "iotedgedevice_lte_fail_over_message_3": "mdi:alert-circle-outline",
    "iotedgedevice_lte_fail_over_message_4": "mdi:alert-circle-outline",
    "iotedgedevice_lte_failover_result": "mdi:cellphone-cog",
    "iotedgedevice_lte_modem_firmware_version": "mdi:chip",
    "iotedgedevice_lte_modem_type": "mdi:chip",
    "iotedgedevice_lte_predictor_result_passed": "mdi:cellphone-check",
    "iotedgedevice_lte_quality": "mdi:signal-cellular-3",
    "iotedgedevice_lte_rssi": "mdi:signal-cellular-3",
    "iotedgedevice_lte_state": "mdi:cellphone-settings",
    "iotedgedevice_memory_usage": "mdi:memory",

    # Inverter
    "inverter_running_state": "mdi:run-fast",
    "inverter_system_state": "mdi:cog-sync",
    "inverter_mode_forcible_charge_discharge": "mdi:swap-vertical",
    "inverter_mode_power_active": "mdi:lightning-bolt",
    "inverter_power_factor": "mdi:math-compass",
    "inverter_serialnumber": "mdi:barcode",
    "inverter_setting_charge_from_grid": "mdi:transmission-tower-import",
    "inverter_state_alarmcodes_1": "mdi:alert",
    "inverter_state_alarmcodes_2": "mdi:alert",
    "inverter_state_alarmcodes_3": "mdi:alert",

    # Battery
    "battery_force_chargedischarge_mode": "mdi:swap-vertical",
    "battery_running_state": "mdi:battery-sync",
    "battery_running_state_unit_1": "mdi:battery-sync",
    "battery_running_state_unit_2": "mdi:battery-sync",
    "duration_battery_force_chargedischarge": "mdi:timer",
    "mode_battery_working": "mdi:battery-sync",
    "battery_mode_forcible_charge_discharge": "mdi:swap-vertical",
    "battery_setting_charge_from_grid": "mdi:transmission-tower-import",

    # Wallbox
    "count_wallbox_connector_1_phases_charging": "mdi:flash-triangle",
    "state_wallbox_connector_1_charge": "mdi:car-electric",
    "wallbox_lademodus": "mdi:ev-station",
    "wallbox_status": "mdi:information-outline",

    # Site data
    "site_data_energy_consumption_total_day": "mdi:calendar-today",
    "site_data_energy_consumption_total_lifetime": "mdi:calendar-range",
    "site_data_power_consumption_total": "mdi:flash-auto",

    # Inverter energy & power
    "inverter_current_string_1": "mdi:current-dc",
    "inverter_current_string_2": "mdi:current-dc",
    "inverter_energy_battery_charge_lifetime": "mdi:battery-plus",
    "inverter_energy_battery_discharge_lifetime": "mdi:battery-minus",
    "inverter_energy_grid_export_day": "mdi:transmission-tower-export",
    "inverter_energy_grid_export_lifetime": "mdi:transmission-tower-export",
    "inverter_energy_grid_import_day": "mdi:transmission-tower-import",
    "inverter_energy_grid_import_lifetime": "mdi:transmission-tower-import",
    "inverter_energy_production_total_day": "mdi:solar-power",
    "inverter_energy_production_total_lifetime": "mdi:solar-power",
    "inverter_frequency_grid": "mdi:sine-wave",
    "inverter_grid_import_power_total_calculated": "mdi:flash",
    "inverter_power_ac_phase_a": "mdi:flash",
    "inverter_power_ac_phase_b": "mdi:flash",
    "inverter_power_ac_phase_c": "mdi:flash",
    "inverter_power_active": "mdi:lightning-bolt",
    "inverter_power_active_fixed": "mdi:lightning-bolt-circle",
    "inverter_power_battery_charge_discharge": "mdi:swap-vertical",
    "inverter_power_battery_charge_max": "mdi:battery-arrow-up",
    "inverter_power_dc_string_1": "mdi:flash",
    "inverter_power_dc_string_2": "mdi:flash",
    "inverter_power_dc_total": "mdi:flash",
    "inverter_power_dc_total_calculated": "mdi:flash",
    "inverter_power_dc_total_huawei": "mdi:flash",
    "inverter_power_grid_export": "mdi:transmission-tower-export",
    "inverter_power_grid_export_calculated": "mdi:transmission-tower-export",
    "inverter_power_grid_export_huawei": "mdi:transmission-tower-export",
    "inverter_power_grid_maximum_feed": "mdi:transmission-tower",
    "inverter_power_reactive": "mdi:flash-alert",
    "inverter_temperature_housing_inside": "mdi:thermometer",
    "inverter_voltage_phase_a": "mdi:sine-wave",
    "inverter_voltage_phase_b": "mdi:sine-wave",
    "inverter_voltage_phase_c": "mdi:sine-wave",
    "inverter_voltage_string_1": "mdi:sine-wave",
    "inverter_voltage_string_2": "mdi:sine-wave",
    "inverter_energy_produced_total_dc": "mdi:solar-power",
    "inverter_energy_produced_today_dc": "mdi:solar-power",

    # Battery voltage & current
    "battery_unit_1_voltage": "mdi:car-battery",
    "battery_unit_2_voltage": "mdi:car-battery",
    "battery_unit_3_voltage": "mdi:car-battery",
    "current_battery": "mdi:current-dc",
    "current_battery_unit_1": "mdi:current-dc",
    "current_battery_unit_2": "mdi:current-dc",
    "energy_battery_charge_day": "mdi:battery-plus",
    "energy_battery_discharge_day": "mdi:battery-minus",
    "power_battery_charge_discharge": "mdi:swap-vertical",
    "power_battery_charge_max": "mdi:battery-arrow-up",
    "power_battery_discharge_max": "mdi:battery-arrow-down",
    "power_battery_forcible_charge": "mdi:battery-arrow-up",
    "power_battery_forcible_discharge": "mdi:battery-arrow-down",
    "battery_storage_power_of_charge_from_grid": "mdi:transmission-tower-import",
    "temperature_battery": "mdi:thermometer",
    "voltage_battery": "mdi:car-battery",
    "voltage_battery_unit_1": "mdi:car-battery",
    "voltage_battery_unit_2": "mdi:car-battery",

    # PowerSensor
    "powersensor_current_phase_a": "mdi:current-ac",
    "powersensor_current_phase_b": "mdi:current-ac",
    "powersensor_current_phase_c": "mdi:current-ac",
    "powersensor_power_ac_phase_a": "mdi:flash",
    "powersensor_power_ac_phase_b": "mdi:flash",
    "powersensor_power_ac_phase_c": "mdi:flash",
    "powersensor_voltage_phase_a": "mdi:sine-wave",
    "powersensor_voltage_phase_b": "mdi:sine-wave",
    "powersensor_voltage_phase_c": "mdi:sine-wave",

    # Wallbox connector
    "current_wallbox_connector_1_phase_a": "mdi:current-ac",
    "current_wallbox_connector_1_phase_b": "mdi:current-ac",
    "current_wallbox_connector_1_phase_c": "mdi:current-ac",
    "energy_wallbox_connector_1_charged_total": "mdi:ev-station",
    "power_wallbox_connector_1_charging": "mdi:ev-station",
    "power_wallbox_connector_1_offered": "mdi:ev-plug-type2",
    "voltage_wallbox_connector_1_phase_a": "mdi:transmission-tower",
    "voltage_wallbox_connector_1_phase_b": "mdi:transmission-tower",
    "voltage_wallbox_connector_1_phase_c": "mdi:transmission-tower",

    # Inverter System State bits
    "inverter_system_state_decimal": "mdi:numeric",
    "inverter_system_state_flags": "mdi:state-machine",
    "inverter_system_state_standby": "mdi:pause-circle",
    "inverter_system_state_grid_connected": "mdi:transmission-tower",
    "inverter_system_state_grid_connected_normally": "mdi:check-circle",
    "inverter_system_state_grid_derating_power_rationing": "mdi:gauge-low",
    "inverter_system_state_grid_derating_internal_cause": "mdi:gauge-low",
    "inverter_system_state_normal_stop": "mdi:stop-circle",
    "inverter_system_state_stop_due_to_faults": "mdi:alert-circle",
    "inverter_system_state_stop_due_to_power_rationing": "mdi:flash-off",
    "inverter_system_state_shutdown": "mdi:power",
    "inverter_system_state_spot_check": "mdi:magnify",

    # Heatpump
    "heatpump_domestichotwater_temperature": "mdi:water-thermometer",
    "heatpump_energy_consumption_total_lifetime": "mdi:lightning-bolt",
    "heatpump_operation_mode_midea": "mdi:heat-pump-outline",
    "heatpump_outside_temperature": "mdi:thermometer",
    "heatpump_power_consumption_total": "mdi:heat-pump",
}

