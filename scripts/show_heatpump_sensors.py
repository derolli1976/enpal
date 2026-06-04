#!/usr/bin/env python3
"""
Zeigt die Heatpump-Sensoren aus dem realen HTML mit allen Attributen
"""
from custom_components.enpal_webparser.utils import parse_enpal_html_sensors

# Lade die reale HTML-Datei
with open('custom_components/enpal_webparser/tests/fixtures/deviceMessagesHP.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Parse nur Heatpump-Sensoren
sensors = parse_enpal_html_sensors(html, selected_groups=['Heatpump'])

print(f'\n🔥 Gefundene Heatpump-Sensoren: {len(sensors)}\n')
print('=' * 100)

for i, sensor in enumerate(sensors, 1):
    print(f'\n{i}. {sensor["name"]}')
    print(f'   {"Unique ID:":<20} {sensor["unique_id"]}')
    print(f'   {"Wert (raw):":<20} {sensor["value"]}')
    print(f'   {"Einheit:":<20} {sensor.get("unit") or "—"}')
    print(f'   {"Device Class:":<20} {sensor.get("device_class") or "—"}')
    print(f'   {"State Class:":<20} {sensor.get("state_class") or "—"}')
    print(f'   {"Icon:":<20} {sensor.get("icon") or "mdi:flash (standard)"}')
    print(f'   {"Enabled:":<20} {sensor.get("enabled", True)}')
    print(f'   {"Letztes Update:":<20} {sensor.get("enpal_last_update", "unbekannt")}')

print('\n' + '=' * 100)
print(f'\n✅ Alle {len(sensors)} Heatpump-Sensoren erfolgreich geparst\n')
