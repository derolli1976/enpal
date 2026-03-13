# WebSocket PoC - Testanleitung

## ✅ Was wurde erstellt?

### Projektstruktur
```
custom_components/enpal_webparser/
├── api/
│   ├── __init__.py          # Package exports
│   ├── base.py              # Abstract EnpalApiClient
│   ├── protocol.py          # Blazor SignalR protocol helpers
│   └── websocket_client.py  # WebSocket client implementation
├── models.py                # Data models (CollectorData, etc.)
└── ...

test_websocket_poc.py        # PoC test script
```

### Dependencies
- ✅ `msgpack>=1.0.7` installiert
- ✅ requirements.txt aktualisiert
- ✅ manifest.json aktualisiert

## 🚀 PoC testen

### 1. IP-Adresse der Enpal Box finden

**Option A - Router:**
Schaue im Router nach DHCP-Einträgen für ein Gerät mit Namen wie "enpal" oder "collector"

**Option B - Netzwerk-Scan:**
```powershell
# Schnell-Scan (empfohlen)
1..254 | ForEach-Object {
    $ip = "192.168.1.$_"
    if (Test-Connection -ComputerName $ip -Count 1 -Quiet) {
        try {
            $response = Invoke-WebRequest -Uri "http://$ip/collector" -TimeoutSec 1 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "✅ Enpal Box gefunden: $ip" -ForegroundColor Green
            }
        } catch {}
    }
}
```

### 2. Test ausführen

```powershell
# Aktiviere venv falls noch nicht geschehen
.\.venv\Scripts\Activate.ps1

# Führe PoC-Test aus
python test_websocket_poc.py <ENPAL_BOX_IP>

# Beispiel:
python test_websocket_poc.py 192.168.1.100
```

### 3. Was passiert?

Der Test durchläuft folgende Schritte:

1. **Connect**: WebSocket-Verbindung aufbauen
   - HTTP GET /collector → Blazor-Komponenten extrahieren
   - POST /_blazor/negotiate → Connection Token holen
   - WebSocket ws://.../_blazor?id=<token> verbinden
   - Blazor Handshake durchführen
   - StartCircuit senden
   - UpdateRootComponents senden

2. **Fetch Data**: Button-Click simulieren
   - EventHandler ID 4 ("Load Current Collector State")
   - Warte auf blazorMonaco.editor.setValue callback
   - JSON-Daten extrahieren

3. **Display Results**: Daten anzeigen
   - Collection ID
   - IoT Device ID
   - Anzahl Device Collections
   - Erste 3 Datenpunkte pro Gerät
   - Speichere vollständige Daten in `websocket_poc_data.json`

4. **Cleanup**: Verbindung schließen

## 📊 Erwartete Ausgabe

```
================================================================================
Enpal WebSocket Client - Proof of Concept
================================================================================

[1/3] Connecting to Enpal Box...
✅ Connection established!

[2/3] Fetching collector data...
✅ Data received!

[3/3] Parsing results...

================================================================================
COLLECTOR DATA SUMMARY
================================================================================

Collection ID:  abc-123-def-456
IoT Device ID:  enpal-box-12345
Timestamp:      2025-12-26T14:30:00Z

Device Collections: 5

  [1] Inverter
      Device ID:  inv-001
      Data Points: 24 numeric, 8 text
      Sample Data:
        - Power.AC.Total: 3456.7 W
        - Power.DC.Total: 3567.2 W
        - Energy.AC.Total: 12345.6 kWh

  [2] Battery
      Device ID:  bat-001
      Data Points: 15 numeric, 5 text
      Sample Data:
        - StateOfCharge: 85.5 %
        - Power.Charge: 1234.5 W
        - Voltage: 52.3 V

  [3] Wallbox
      Device ID:  wb-001
      Data Points: 12 numeric, 4 text
      Sample Data:
        - ChargingPower: 11000 W
        - ChargingEnergy: 25.3 kWh
        - Status: Charging

  [4] PowerSensor
      Device ID:  ps-001
      Data Points: 8 numeric, 2 text

  [5] Heatpump
      Device ID:  hp-001
      Data Points: 18 numeric, 6 text

💾 Full data saved to: websocket_poc_data.json

================================================================================
✅ Proof of Concept SUCCESSFUL!
================================================================================

[Cleanup] Closing connection...
✅ Connection closed
```

## 🐛 Troubleshooting

### Error: "No Blazor components found"
- Prüfe ob `/collector` Seite im Browser funktioniert
- Eventuell ist es ein Gen-2 Enpal-System (nicht unterstützt)

### Error: "HTTP 401" oder "HTTP 403"
- Enpal Box erfordert eventuell Authentifizierung
- Prüfe Browser-Netzwerk-Tab für Auth-Details

### Error: "Connection refused"
- Falsche IP-Adresse
- Enpal Box ist offline
- Firewall blockiert Port 80/WebSocket

### Error: "Timeout waiting for data"
- Event Handler ID könnte anders sein
- Prüfe Browser DevTools → Network → WS für echte Event IDs

## 📝 Nächste Schritte nach erfolgreichem PoC

1. **Event Handler IDs dokumentieren**
   - Welche ID ist "Load Collector State"?
   - Welche IDs sind Wallbox-Steuerung?

2. **Datenstruktur analysieren**
   - `websocket_poc_data.json` untersuchen
   - Mit HTML-Parser-Daten vergleichen
   - Mapping erstellen

3. **Coordinator integrieren**
   - WebSocket-Client in DataUpdateCoordinator einbauen
   - Persistent Connection für regelmäßige Updates

4. **Config Flow erweitern**
   - WebSocket vs HTML Parsing Option
   - Auto-Detection ob WebSocket verfügbar

## 🎉 Success Criteria

- ✅ Verbindung aufgebaut ohne Fehler
- ✅ JSON-Daten erhalten
- ✅ DeviceCollections enthält mindestens 1 Gerät
- ✅ Datenpunkte sind vorhanden
- ✅ Timestamps sind aktuell
- ✅ Verbindung sauber geschlossen

Wenn alle Punkte erfüllt sind: **PoC erfolgreich!** 🚀
