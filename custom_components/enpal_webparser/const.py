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
DEFAULT_TIMEOUT = 30

# --- Firmware ---
# Minimum Enpal firmware (major, minor) required for WebSocket mode and native
# wallbox control (Solar Rel. 8.50). Older firmware only supports HTML polling.
WEBSOCKET_MIN_FIRMWARE = (8, 50)

DEFAULT_GROUPS = [
    "Wallbox",
    "Battery",
    "Inverter",
    "Site Data",
    "IoTEdgeDevice",
    "PowerSensor",
    "Heatpump",
]

DEFAULT_USE_WALLBOX = False

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
    "full": "Full",
    "solar": "Solar",
    "smart": "Smart",
}

# Legacy mapping for backward compatibility (addon used "fast" for "Full")
WALLBOX_LEGACY_MODE_MAP = {
    "fast": "full",
}

# --- Wallbox native sources (firmware 8.50) ---
# Since firmware 8.50 the wallbox charge mode and connection state are exposed
# directly on /deviceMessages (group "Wallbox"). These are the make_id() keys of
# the raw sensors we prefer when feeding the dedicated "Wallbox Lademodus" and
# "Wallbox Status" sensors, in priority order. Used for auto-detection when the
# user has not explicitly selected a source in the options flow.
WALLBOX_MODE_SOURCE_CANDIDATES = [
    "wallbox_mode_charge_connector_1",  # Mode.Charge.Connector.1 -> Solar/Eco/Fast
]
WALLBOX_STATUS_SOURCE_CANDIDATES = [
    # Status.Wallbox.Connector.1 -> Available/Charging (reflects the vehicle/charge state).
    # NOTE: Status.Wallbox.Connected only indicates whether a wallbox is attached
    # at all (1/0), NOT the vehicle connection/charge state, so it is intentionally
    # NOT used here.
    "status_wallbox_connector_1",
    # Some firmware variants (e.g. Enpal ArC GEN2 SW 2.3.1) expose the same value
    # as Status.Connector.1 -> "Wallbox: Status Connector 1" -> this key instead.
    "wallbox_status_connector_1",
]

# --- Sensor key aliases (firmware 8.51) ---
# Firmware 8.51 appended an ".Inverter" suffix to several data points in the
# "Inverter" group. Mapping them back to the previous key keeps the existing
# entity ids, history and automations intact instead of creating duplicates.
SENSOR_KEY_ALIASES = {
    "Energy.Battery.Charge.Day.Inverter": "Energy.Battery.Charge.Day",
    "Energy.Battery.Discharge.Day.Inverter": "Energy.Battery.Discharge.Day",
    "Mode.Forcible.Charge.Discharge.Inverter": "Mode.Forcible.Charge.Discharge",
    "Power.AC.Phase.A.Inverter": "Power.AC.Phase.A",
    "Power.AC.Phase.B.Inverter": "Power.AC.Phase.B",
    "Power.AC.Phase.C.Inverter": "Power.AC.Phase.C",
    "Power.Battery.Charge.Discharge.Inverter": "Power.Battery.Charge.Discharge",
    "Power.Battery.Charge.Max.Inverter": "Power.Battery.Charge.Max",
    "Power.Battery.Discharge.Max.Inverter": "Power.Battery.Discharge.Max",
}

# --- Sensor key to group mapping (firmware 8.51) ---
# On firmware 8.51 the HTTP response of /deviceMessages no longer contains the
# device rows; they only arrive through the Blazor WebSocket RenderBatch diffs.
# Those diffs carry the raw dotted key but not the card (group) the row belongs
# to. This table restores the group so new sensors get the same entity ids as
# they would from HTML parsing. Generated from the deviceMessages fixtures
# (8.50 + 8.51); keys that appear in more than one group within a firmware are
# deliberately absent.
SENSOR_KEY_GROUPS = {
    "Battery.Force.ChargeDisCharge.Mode": "Battery",
    "Battery.Running.State": "Battery",
    "Battery.Running.State.Unit.1": "Battery",
    "Battery.Running.State.Unit.2": "Battery",
    "Battery.Unit.1.Voltage": "Battery",
    "Battery.Unit.2.Voltage": "Battery",
    "Battery.Unit.3.Voltage": "Battery",
    "ChargeBox.SerialNumber": "Wallbox",
    "ChargePoint.SerialNumber": "Wallbox",
    "ChargePoint.SerialNumber.Property": "Wallbox",
    "Count.Wallbox.Connector.1.Phases.Charging": "Wallbox",
    "Cpu.Load": "IoTEdgeDevice",
    "Current.Battery": "Battery",
    "Current.Battery.Unit.1": "Battery",
    "Current.Battery.Unit.2": "Battery",
    "Current.Phase.A": "PowerSensor",
    "Current.Phase.B": "PowerSensor",
    "Current.Phase.C": "PowerSensor",
    "Current.String.1": "Inverter",
    "Current.String.2": "Inverter",
    "Current.Wallbox.Connector.1.Phase.A": "Wallbox",
    "Current.Wallbox.Connector.1.Phase.B": "Wallbox",
    "Current.Wallbox.Connector.1.Phase.C": "Wallbox",
    "Device.Name": "IoTEdgeDevice",
    "Duration.Battery.Force.ChargeDisCharge": "Battery",
    "Energy.Battery.Charge.Day": "Battery",
    "Energy.Battery.Charge.Day.Inverter": "Inverter",
    "Energy.Battery.Charge.Level": "Battery",
    "Energy.Battery.Charge.Level.Unit.1": "Battery",
    "Energy.Battery.Charge.Level.Unit.2": "Battery",
    "Energy.Battery.Charge.Lifetime": "Inverter",
    "Energy.Battery.Discharge.Day": "Battery",
    "Energy.Battery.Discharge.Day.Inverter": "Inverter",
    "Energy.Battery.Discharge.Lifetime": "Inverter",
    "Energy.Consumption.Total.Day": "Site Data",
    "Energy.Consumption.Total.Lifetime": "Site Data",
    "Energy.Grid.Export.Day": "Inverter",
    "Energy.Grid.Export.Lifetime": "Inverter",
    "Energy.Grid.Import.Day": "Inverter",
    "Energy.Grid.Import.Lifetime": "Inverter",
    "Energy.Production.Total.Day": "Inverter",
    "Energy.Production.Total.Lifetime": "Inverter",
    "Energy.Wallbox.Connector.1.Charged.Total": "Wallbox",
    "Frequency.Grid": "Inverter",
    "Generation.HW": "IoTEdgeDevice",
    "Generation.SW": "IoTEdgeDevice",
    "Grid.Import.Power.Total.Calculated": "Inverter",
    "HW.Cronny.Result": "IoTEdgeDevice",
    "Inverter.Power.Total": "Inverter",
    "Inverter.Running.State": "Inverter",
    "Inverter.System.State": "Inverter",
    "IoT.Data.Consumption.Lan.Down.Month": "IoTEdgeDevice",
    "IoT.Data.Consumption.Lan.Up.Month": "IoTEdgeDevice",
    "IoT.Data.Consumption.Lte.Down.Month": "IoTEdgeDevice",
    "IoT.Data.Consumption.Lte.Up.Month": "IoTEdgeDevice",
    "IoT.MainState": "IoTEdgeDevice",
    "IoTEdgeDevice.Device.Type": "IoTEdgeDevice",
    "IoTEdgeDevice.SerialNumber": "IoTEdgeDevice",
    "LTE.CellularGuard.MmRestart.Count": "IoTEdgeDevice",
    "LTE.CellularGuard.MmRestart.CountSuccess": "IoTEdgeDevice",
    "LTE.CellularGuard.MmRestart.LastTime": "IoTEdgeDevice",
    "LTE.CellularGuard.MmRestart.LastTimeSuccess": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemAirplaneModeSwitch.Count": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemAirplaneModeSwitch.CountSuccess": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemAirplaneModeSwitch.LastTime": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemAirplaneModeSwitch.LastTimeSuccess": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemFrequencyClear.Count": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemFrequencyClear.CountSuccess": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemFrequencyClear.LastTime": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemFrequencyClear.LastTimeSuccess": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemHardReset.Count": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemHardReset.CountSuccess": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemHardReset.LastTime": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemHardReset.LastTimeSuccess": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemManagerErr.Count": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemManagerErr.LastTime": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemSoftReset.Count": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemSoftReset.CountSuccess": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemSoftReset.LastTime": "IoTEdgeDevice",
    "LTE.CellularGuard.ModemSoftReset.LastTimeSuccess": "IoTEdgeDevice",
    "LTE.CellularGuard.NetworkError.Count": "IoTEdgeDevice",
    "LTE.CellularGuard.NetworkError.LastTime": "IoTEdgeDevice",
    "LTE.CellularGuard.NetworkErrorLowSignal.Count": "IoTEdgeDevice",
    "LTE.CellularGuard.NetworkErrorLowSignal.LastTime": "IoTEdgeDevice",
    "LTE.CellularGuard.NetworkErrorNoIp.Count": "IoTEdgeDevice",
    "LTE.CellularGuard.NetworkErrorNoIp.LastTime": "IoTEdgeDevice",
    "LTE.CellularGuard.Result.Timestamp": "IoTEdgeDevice",
    "LTE.CellularGuard.Result.Value": "IoTEdgeDevice",
    "LTE.CellularGuard.Result.Version": "IoTEdgeDevice",
    "LTE.CellularGuard.SimError.Count": "IoTEdgeDevice",
    "LTE.CellularGuard.SimError.LastTime": "IoTEdgeDevice",
    "LTE.CellularGuard.SimError10.Count": "IoTEdgeDevice",
    "LTE.CellularGuard.SimError10.LastTime": "IoTEdgeDevice",
    "LTE.Connection.Type": "IoTEdgeDevice",
    "LTE.Cronny.Result": "IoTEdgeDevice",
    "LTE.Fail-over.Message.0": "IoTEdgeDevice",
    "LTE.Fail-over.Message.1": "IoTEdgeDevice",
    "LTE.Fail-over.Message.2": "IoTEdgeDevice",
    "LTE.Fail-over.Message.3": "IoTEdgeDevice",
    "LTE.Fail-over.Message.4": "IoTEdgeDevice",
    "LTE.Failover.Result": "IoTEdgeDevice",
    "LTE.Modem.Firmware.Version": "IoTEdgeDevice",
    "LTE.Modem.Type": "IoTEdgeDevice",
    "LTE.Predictor.Id": "IoTEdgeDevice",
    "LTE.Predictor.Result.Passed": "IoTEdgeDevice",
    "LTE.Quality": "IoTEdgeDevice",
    "LTE.RSRP": "IoTEdgeDevice",
    "LTE.RSRQ": "IoTEdgeDevice",
    "LTE.RSSI": "IoTEdgeDevice",
    "LTE.SNR": "IoTEdgeDevice",
    "LTE.State": "IoTEdgeDevice",
    "Memory.Usage": "IoTEdgeDevice",
    "Meter.Connect.State": "PowerSensor",
    "Meter.Enable.Disable": "PowerSensor",
    "Meter2.AC.Phase.A": "PowerSensor",
    "Meter2.AC.Phase.B": "PowerSensor",
    "Meter2.AC.Phase.C": "PowerSensor",
    "Meter2.AC.Total": "PowerSensor",
    "Meter2.Connect.State": "PowerSensor",
    "Meter2.Enable.Disable": "PowerSensor",
    "Mode.Battery.Working": "Battery",
    "Mode.Charge.Connector.1": "Wallbox",
    "Mode.Forcible.Charge.Discharge.Inverter": "Inverter",
    "Mode.Power.Active": "Inverter",
    "Power.AC.Max.Battery": "Battery",
    "Power.AC.Phase.A": "PowerSensor",
    "Power.AC.Phase.A.Inverter": "Inverter",
    "Power.AC.Phase.B": "PowerSensor",
    "Power.AC.Phase.B.Inverter": "Inverter",
    "Power.AC.Phase.C": "PowerSensor",
    "Power.AC.Phase.C.Inverter": "Inverter",
    "Power.Active": "Inverter",
    "Power.Active.Fixed": "Inverter",
    "Power.Battery.Charge.Discharge.Inverter": "Inverter",
    "Power.Battery.Charge.Max.Inverter": "Inverter",
    "Power.Battery.Discharge.Max": "Battery",
    "Power.Battery.Discharge.Max.Inverter": "Inverter",
    "Power.Battery.Forcible.Charge": "Battery",
    "Power.Battery.Forcible.DisCharge": "Battery",
    "Power.Consumption.AC": "Site Data",
    "Power.Consumption.Total": "Site Data",
    "Power.DC.String.1": "Inverter",
    "Power.DC.String.2": "Inverter",
    "Power.DC.Total": "Inverter",
    "Power.DC.Total.Calculated": "Inverter",
    "Power.DC.Total.Huawei": "Inverter",
    "Power.Factor": "PowerSensor",
    "Power.Grid.Export": "Inverter",
    "Power.Grid.Export.Calculated": "Inverter",
    "Power.Grid.Export.Huawei": "Inverter",
    "Power.Grid.Maximum.Feed": "Inverter",
    "Power.Reactive": "PowerSensor",
    "Power.Wallbox.Connector.1.Charging": "Wallbox",
    "Power.Wallbox.Connector.1.Charging.Requested": "Wallbox",
    "Power.Wallbox.Connector.1.Offered": "Wallbox",
    "SerialNumber.Battery.Unit.1": "Battery",
    "SerialNumber.Battery.Unit.2": "Battery",
    "State.AlarmCodes.1": "Inverter",
    "State.AlarmCodes.2": "Inverter",
    "State.AlarmCodes.3": "Inverter",
    "State.Wallbox.Connector.1.Charge": "Wallbox",
    "Status.Wallbox.Connected": "Wallbox",
    "Status.Wallbox.Connector.1": "Wallbox",
    "Storage.Power.Of.Charge.From.Grid": "Battery",
    "Temperature.Battery": "Battery",
    "Temperature.Housing.Inside": "Inverter",
    "Version.SW.Wallbox": "Wallbox",
    "Voltage.Battery": "Battery",
    "Voltage.Battery.Unit.1": "Battery",
    "Voltage.Battery.Unit.2": "Battery",
    "Voltage.Phase.A": "PowerSensor",
    "Voltage.Phase.B": "PowerSensor",
    "Voltage.Phase.C": "PowerSensor",
    "Voltage.String.1": "Inverter",
    "Voltage.String.2": "Inverter",
    "Voltage.Wallbox.Connector.1.Phase.A": "Wallbox",
    "Voltage.Wallbox.Connector.1.Phase.B": "Wallbox",
    "Voltage.Wallbox.Connector.1.Phase.C": "Wallbox",
    "Wallbox.DeviceId": "Wallbox",
    "Wallbox.Settings.AutomaticChargeStatus.Connector.1": "Wallbox",
    "Wallbox.Settings.GunLockStatus.Connector.1": "Wallbox",
    "Wallbox.Settings.MinimumChargeCurrent.Connector.1": "Wallbox",
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

