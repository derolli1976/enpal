#!/usr/bin/env python3
"""
Schnelle Analyse: HTML vs WebSocket Sensoren

Zählt einfach die Sensoren in beiden Dateien.
"""
import json
from pathlib import Path
from bs4 import BeautifulSoup


def extract_html_sensors():
    """Extrahiere Sensor-Namen aus HTML"""
    html_file = Path("custom_components/enpal_webparser/tests/website.html")
    html = html_file.read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    
    sensors = {}
    cards = soup.find_all("div", class_="card")
    
    for card in cards:
        h2 = card.find("h2")
        if not h2:
            continue
        
        group = h2.get_text(strip=True)
        table = card.find("table")
        if not table:
            continue
        
        sensors[group] = []
        
        rows = table.find_all("tr")
        for row in rows:
            tds = row.find_all("td")
            if len(tds) >= 2:
                name = tds[0].get_text(strip=True)
                value = tds[1].get_text(strip=True)
                if name and value:
                    full_name = f"{group}: {name}"
                    sensors[group].append(full_name)
    
    return sensors


def extract_websocket_sensors():
    """Extrahiere Sensor-Namen aus WebSocket JSON"""
    ws_file = Path("custom_components/enpal_webparser/tests/websocket.json")
    
    with open(ws_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    sensors = {}
    
    # Device Collections
    for device in data.get("DeviceCollections", []):
        device_class = device.get("deviceClass", "Unknown")
        
        if device_class not in sensors:
            sensors[device_class] = []
        
        # Number data points
        for key, value in device.get("numberDataPoints", {}).items():
            sensor_name = key.replace(".", " ")
            full_name = f"{device_class}: {sensor_name}"
            sensors[device_class].append(full_name)
        
        # Text data points
        for key, value in device.get("textDataPoints", {}).items():
            sensor_name = key.replace(".", " ")
            full_name = f"{device_class}: {sensor_name}"
            sensors[device_class].append(full_name)
    
    # Site Data (top-level)
    site_data = []
    for key in data.get("numberDataPoints", {}).keys():
        sensor_name = key.replace(".", " ")
        full_name = f"Site Data: {sensor_name}"
        site_data.append(full_name)
    
    if site_data:
        sensors["Site Data"] = site_data
    
    return sensors


def main():
    print("=" * 100)
    print("SENSOR-VERGLEICH: HTML vs. WebSocket")
    print("=" * 100)
    print()
    
    # Extrahiere Sensoren
    print("📄 Extrahiere HTML-Sensoren...")
    html_sensors = extract_html_sensors()
    html_total = sum(len(v) for v in html_sensors.values())
    print(f"   ✓ {html_total} Sensoren gefunden")
    
    print("🔌 Extrahiere WebSocket-Sensoren...")
    ws_sensors = extract_websocket_sensors()
    ws_total = sum(len(v) for v in ws_sensors.values())
    print(f"   ✓ {ws_total} Sensoren gefunden")
    print()
    
    # Gesamtstatistik
    print("=" * 100)
    print("📊 GESAMTSTATISTIK")
    print("=" * 100)
    print()
    print(f"  HTML:      {html_total:3d} Sensoren")
    print(f"  WebSocket: {ws_total:3d} Sensoren")
    print(f"  Differenz: {abs(html_total - ws_total):3d} Sensoren")
    print()
    
    # Vergleich pro Gruppe
    print("=" * 100)
    print("📋 VERGLEICH PRO GRUPPE")
    print("=" * 100)
    print()
    
    all_groups = sorted(set(list(html_sensors.keys()) + list(ws_sensors.keys())))
    
    print(f"{'Gruppe':<20} {'HTML':>10} {'WebSocket':>12} {'Differenz':>12}")
    print("-" * 100)
    
    for group in all_groups:
        html_count = len(html_sensors.get(group, []))
        ws_count = len(ws_sensors.get(group, []))
        diff = ws_count - html_count
        diff_str = f"{diff:+d}" if diff != 0 else "0"
        
        print(f"{group:<20} {html_count:>10} {ws_count:>12} {diff_str:>12}")
    
    print()
    
    # Detaillierter Vergleich
    print("=" * 100)
    print("🔍 DETAILLIERTER VERGLEICH")
    print("=" * 100)
    print()
    
    for group in all_groups:
        html_names = set(html_sensors.get(group, []))
        ws_names = set(ws_sensors.get(group, []))
        
        only_html = html_names - ws_names
        only_ws = ws_names - html_names
        in_both = html_names & ws_names
        
        print(f"Gruppe: {group}")
        print(f"  In beiden:      {len(in_both):3d}")
        print(f"  Nur HTML:       {len(only_html):3d}")
        print(f"  Nur WebSocket:  {len(only_ws):3d}")
        
        if only_html:
            print(f"\n  🔴 Nur in HTML:")
            for name in sorted(only_html)[:5]:  # Nur erste 5
                print(f"    - {name}")
            if len(only_html) > 5:
                print(f"    ... und {len(only_html) - 5} weitere")
        
        if only_ws:
            print(f"\n  🟢 Nur in WebSocket:")
            for name in sorted(only_ws)[:5]:  # Nur erste 5
                print(f"    - {name}")
            if len(only_ws) > 5:
                print(f"    ... und {len(only_ws) - 5} weitere")
        
        print()
    
    # Zusammenfassung
    print("=" * 100)
    print("💡 ZUSAMMENFASSUNG")
    print("=" * 100)
    print()
    
    html_all = set()
    ws_all = set()
    for v in html_sensors.values():
        html_all.update(v)
    for v in ws_sensors.values():
        ws_all.update(v)
    
    only_html_total = len(html_all - ws_all)
    only_ws_total = len(ws_all - html_all)
    in_both_total = len(html_all & ws_all)
    
    if only_html_total > 0:
        print(f"  ⚠️  {only_html_total} Sensoren sind NUR in HTML verfügbar")
    
    if only_ws_total > 0:
        print(f"  ⚠️  {only_ws_total} Sensoren sind NUR in WebSocket verfügbar")
    
    if only_html_total == 0 and only_ws_total == 0:
        print("  ✅ Beide Datenquellen haben exakt die gleichen Sensoren!")
    
    overlap_percent = (in_both_total / max(len(html_all), len(ws_all))) * 100
    print(f"  📊 Übereinstimmung: {overlap_percent:.1f}%")
    print()
    
    # Empfehlung
    if only_html_total > only_ws_total:
        print("  💡 EMPFEHLUNG: HTML als Standard verwenden (mehr Sensoren)")
    elif only_ws_total > only_html_total:
        print("  💡 EMPFEHLUNG: WebSocket als Standard verwenden (mehr Sensoren)")
    else:
        print("  💡 EMPFEHLUNG: WebSocket verwenden (Echtzeit-Updates, gleiche Anzahl)")
    
    print()


if __name__ == "__main__":
    main()
