#!/usr/bin/env python3
"""
Analyse der Unterschiede zwischen HTML und WebSocket Daten

Vergleicht welche Sensoren in HTML vs. WebSocket verfügbar sind.
"""
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup

# Import Parser
parser_file = Path('custom_components/enpal_webparser/api/websocket_parser.py')
spec = __import__('importlib.util').util.spec_from_file_location("websocket_parser", parser_file)
websocket_parser = __import__('importlib.util').util.module_from_spec(spec)
spec.loader.exec_module(websocket_parser)
parse_websocket_json_to_sensors = websocket_parser.parse_websocket_json_to_sensors

# Import HTML parser
utils_file = Path('custom_components/enpal_webparser/utils.py')
utils_spec = __import__('importlib.util').util.spec_from_file_location("utils_parser", utils_file)
utils_parser = __import__('importlib.util').util.module_from_spec(utils_spec)

# Manually inject const module to avoid import issues
const_file = Path('custom_components/enpal_webparser/const.py')
const_spec = __import__('importlib.util').util.spec_from_file_location("const", const_file)
const_module = __import__('importlib.util').util.module_from_spec(const_spec)
const_spec.loader.exec_module(const_module)
sys.modules['const'] = const_module

utils_spec.loader.exec_module(utils_parser)
parse_enpal_html_sensors = utils_parser.parse_enpal_html_sensors


def analyze_differences():
    """Analysiere Unterschiede zwischen HTML und WebSocket"""
    
    print("=" * 100)
    print("SENSOR-VERGLEICH: HTML vs. WebSocket")
    print("=" * 100)
    print()
    
    # Lade Daten
    html_file = Path("custom_components/enpal_webparser/tests/website.html")
    ws_file = Path("custom_components/enpal_webparser/tests/websocket.json")
    
    if not html_file.exists():
        print(f"❌ HTML-Datei nicht gefunden: {html_file}")
        return False
    
    if not ws_file.exists():
        print(f"❌ WebSocket-Datei nicht gefunden: {ws_file}")
        return False
    
    # Parse HTML
    print("📄 Parse HTML...")
    html_content = html_file.read_text(encoding='utf-8')
    groups = ['Battery', 'Inverter', 'IoTEdgeDevice', 'PowerSensor', 'Wallbox', 'Site Data']
    html_sensors = parse_enpal_html_sensors(html_content, groups)
    print(f"   ✓ {len(html_sensors)} Sensoren gefunden")
    
    # Parse WebSocket
    print("🔌 Parse WebSocket...")
    with open(ws_file, 'r', encoding='utf-8') as f:
        ws_data = json.load(f)
    ws_sensors = parse_websocket_json_to_sensors(ws_data, groups)
    print(f"   ✓ {len(ws_sensors)} Sensoren gefunden")
    print()
    
    # Erstelle Sets von Sensor-Namen
    html_names = {s['name'] for s in html_sensors}
    ws_names = {s['name'] for s in ws_sensors}
    
    # Gruppiere nach Group
    def group_sensors(sensors):
        by_group = {}
        for s in sensors:
            group = s.get('group', 'Unknown')
            by_group.setdefault(group, []).append(s['name'])
        return by_group
    
    html_by_group = group_sensors(html_sensors)
    ws_by_group = group_sensors(ws_sensors)
    
    # Gesamtstatistik
    print("=" * 100)
    print("📊 GESAMTSTATISTIK")
    print("=" * 100)
    print()
    print(f"  HTML:      {len(html_sensors):3d} Sensoren")
    print(f"  WebSocket: {len(ws_sensors):3d} Sensoren")
    print(f"  Differenz: {abs(len(html_sensors) - len(ws_sensors)):3d} Sensoren")
    print()
    
    # Vergleich pro Gruppe
    print("=" * 100)
    print("📋 VERGLEICH PRO GRUPPE")
    print("=" * 100)
    print()
    
    all_groups = sorted(set(list(html_by_group.keys()) + list(ws_by_group.keys())))
    
    print(f"{'Gruppe':<20} {'HTML':>10} {'WebSocket':>12} {'Differenz':>12}")
    print("-" * 100)
    
    for group in all_groups:
        html_count = len(html_by_group.get(group, []))
        ws_count = len(ws_by_group.get(group, []))
        diff = ws_count - html_count
        diff_str = f"{diff:+d}" if diff != 0 else "0"
        
        print(f"{group:<20} {html_count:>10} {ws_count:>12} {diff_str:>12}")
    
    print()
    
    # Sensoren nur in HTML
    only_html = html_names - ws_names
    if only_html:
        print("=" * 100)
        print(f"🔴 NUR IN HTML ({len(only_html)} Sensoren)")
        print("=" * 100)
        print()
        
        # Gruppiere nach Group
        only_html_sensors = [s for s in html_sensors if s['name'] in only_html]
        by_group = group_sensors(only_html_sensors)
        
        for group in sorted(by_group.keys()):
            print(f"  {group}:")
            for name in sorted(by_group[group]):
                print(f"    - {name}")
            print()
    
    # Sensoren nur in WebSocket
    only_ws = ws_names - html_names
    if only_ws:
        print("=" * 100)
        print(f"🟢 NUR IN WEBSOCKET ({len(only_ws)} Sensoren)")
        print("=" * 100)
        print()
        
        # Gruppiere nach Group
        only_ws_sensors = [s for s in ws_sensors if s['name'] in only_ws]
        by_group = group_sensors(only_ws_sensors)
        
        for group in sorted(by_group.keys()):
            print(f"  {group}:")
            for name in sorted(by_group[group]):
                print(f"    - {name}")
            print()
    
    # Sensoren in beiden
    in_both = html_names & ws_names
    print("=" * 100)
    print(f"✅ IN BEIDEN VORHANDEN ({len(in_both)} Sensoren)")
    print("=" * 100)
    print()
    
    # Gruppiere
    both_sensors = [s for s in html_sensors if s['name'] in in_both]
    by_group = group_sensors(both_sensors)
    
    for group in sorted(by_group.keys()):
        count = len(by_group[group])
        print(f"  {group:<20}: {count:3d} Sensoren")
    
    print()
    
    # Wert-Vergleich für gemeinsame Sensoren
    print("=" * 100)
    print("🔍 WERT-VERGLEICH (Gemeinsame Sensoren)")
    print("=" * 100)
    print()
    
    html_dict = {s['name']: s for s in html_sensors}
    ws_dict = {s['name']: s for s in ws_sensors}
    
    value_diffs = []
    for name in sorted(in_both):
        html_val = html_dict[name].get('value')
        ws_val = ws_dict[name].get('value')
        
        # Vergleiche Werte (nur wenn beide numerisch)
        if isinstance(html_val, (int, float)) and isinstance(ws_val, (int, float)):
            if abs(html_val - ws_val) > 0.01:  # Kleine Unterschiede ignorieren
                value_diffs.append({
                    'name': name,
                    'html': html_val,
                    'ws': ws_val,
                    'diff': ws_val - html_val
                })
    
    if value_diffs:
        print(f"  {len(value_diffs)} Sensoren mit unterschiedlichen Werten:")
        print()
        for item in value_diffs[:10]:  # Nur erste 10 zeigen
            print(f"    {item['name']}")
            print(f"      HTML:      {item['html']}")
            print(f"      WebSocket: {item['ws']}")
            print(f"      Differenz: {item['diff']:+.2f}")
            print()
        
        if len(value_diffs) > 10:
            print(f"    ... und {len(value_diffs) - 10} weitere")
    else:
        print("  ✅ Alle gemeinsamen Sensoren haben identische Werte!")
    
    print()
    
    # Zusammenfassung
    print("=" * 100)
    print("💡 ZUSAMMENFASSUNG")
    print("=" * 100)
    print()
    
    if len(only_html) > 0:
        print(f"  ⚠️  {len(only_html)} Sensoren sind NUR in HTML verfügbar")
    
    if len(only_ws) > 0:
        print(f"  ⚠️  {len(only_ws)} Sensoren sind NUR in WebSocket verfügbar")
    
    if len(only_html) == 0 and len(only_ws) == 0:
        print("  ✅ Beide Datenquellen haben exakt die gleichen Sensoren!")
    
    overlap_percent = (len(in_both) / max(len(html_names), len(ws_names))) * 100
    print(f"  📊 Übereinstimmung: {overlap_percent:.1f}%")
    print()
    
    # Empfehlung
    if len(only_html) > len(only_ws):
        print("  💡 EMPFEHLUNG: HTML als Standard, da mehr Sensoren")
    elif len(only_ws) > len(only_html):
        print("  💡 EMPFEHLUNG: WebSocket als Standard, da mehr Sensoren")
    else:
        print("  💡 EMPFEHLUNG: WebSocket wegen Echtzeit-Updates (gleiche Sensoren)")
    
    print()
    
    return True


if __name__ == "__main__":
    success = analyze_differences()
    sys.exit(0 if success else 1)
