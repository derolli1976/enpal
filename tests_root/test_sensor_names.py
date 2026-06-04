#!/usr/bin/env python3
"""
Test ob WebSocket-Parser jetzt korrekte Sensor-Namen erstellt
"""
import json
import sys
import importlib.util
from pathlib import Path
from bs4 import BeautifulSoup


def load_parser_module():
    """Lade websocket_parser.py direkt ohne package imports"""
    parser_file = Path("custom_components/enpal_webparser/api/websocket_parser.py")
    
    spec = importlib.util.spec_from_file_location("websocket_parser", parser_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    return module


def extract_html_sensors():
    """Extrahiere Sensor-Namen aus HTML"""
    html_file = Path("custom_components/enpal_webparser/tests/website.html")
    html = html_file.read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    
    sensors = []
    cards = soup.find_all("div", class_="card")
    
    for card in cards:
        h2 = card.find("h2")
        if not h2:
            continue
        
        group = h2.get_text(strip=True)
        table = card.find("table")
        if not table:
            continue
        
        rows = table.find_all("tr")
        for row in rows:
            tds = row.find_all("td")
            if len(tds) >= 2:
                name = tds[0].get_text(strip=True)
                value = tds[1].get_text(strip=True)
                if name and value:
                    full_name = f"{group}: {name}"
                    sensors.append(full_name)
    
    return set(sensors)


def extract_websocket_sensors_live():
    """Extrahiere Sensor-Namen DIREKT vom Parser (nicht aus JSON Datei)"""
    
    parser = load_parser_module()
    
    # Lade Roh-JSON vom WebSocket
    ws_file = Path("custom_components/enpal_webparser/tests/websocket.json")
    
    with open(ws_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # Alle Gruppen aktivieren
    all_groups = ["Battery", "Inverter", "IoTEdgeDevice", "PowerSensor", "Site Data", "Wallbox"]
    
    # Parse mit aktuellem Parser
    result = parser.parse_websocket_json_to_sensors(raw_data, all_groups)
    
    # Extrahiere Sensor-Namen
    sensors = []
    for sensor_data in result:
        name = sensor_data['name']
        sensors.append(name)
    
    return set(sensors)


def main():
    print("="*100)
    print("TEST: WebSocket-Parser Naming")
    print("="*100)
    print()
    
    print("[HTML] Extrahiere HTML-Sensoren...")
    html_sensors = extract_html_sensors()
    print(f"   OK {len(html_sensors)} Sensoren")
    
    print("[WS] Extrahiere WebSocket-Sensoren (mit aktuellem Parser)...")
    ws_sensors = extract_websocket_sensors_live()
    print(f"   OK {len(ws_sensors)} Sensoren")
    
    print()
    print("="*100)
    print("VERGLEICH")
    print("="*100)
    
    # Übereinstimmungen
    in_both = html_sensors & ws_sensors
    only_html = html_sensors - ws_sensors
    only_ws = ws_sensors - html_sensors
    
    print(f"  [OK] In beiden:      {len(in_both):3d}")
    print(f"  [--] Nur HTML:       {len(only_html):3d}")
    print(f"  [++] Nur WebSocket:  {len(only_ws):3d}")
    
    if len(html_sensors) > 0:
        overlap = (len(in_both) / len(html_sensors)) * 100
        print(f"  [%] Uebereinstimmung: {overlap:.1f}%")
    
    print()
    
    # Beispiele
    if in_both:
        print("[OK] BEISPIELE - In beiden:")
        for name in sorted(list(in_both)[:5]):
            print(f"     {name}")
        if len(in_both) > 5:
            print(f"     ... und {len(in_both)-5} weitere")
        print()
    
    if only_html:
        print("[--] BEISPIELE - Nur HTML:")
        for name in sorted(list(only_html)[:5]):
            print(f"     {name}")
        if len(only_html) > 5:
            print(f"     ... und {len(only_html)-5} weitere")
        print()
    
    if only_ws:
        print("[++] BEISPIELE - Nur WebSocket:")
        for name in sorted(list(only_ws)[:5]):
            print(f"     {name}")
        if len(only_ws) > 5:
            print(f"     ... und {len(only_ws)-5} weitere")
    
    print()
    print("="*100)
    
    if overlap > 80:
        print("[OK] ERFOLG: Naming ist kompatibel!")
    elif overlap > 50:
        print(f"[!!] TEILWEISE: {overlap:.1f}% Uebereinstimmung - Verbesserung noetig")
    else:
        print("[XX] FEHLER: Naming ist NICHT kompatibel!")
    
    print()
    print("ALLE Unterschiede:")
    print("-" * 100)
    print("\n[--] Nur HTML (nicht in WebSocket):")
    for name in sorted(only_html):
        print(f"     {name}")
    print(f"\n[++] Nur WebSocket (nicht in HTML):")
    for name in sorted(only_ws):
        print(f"     {name}")
    
    return 0 if overlap > 80 else 1


if __name__ == "__main__":
    sys.exit(main())
