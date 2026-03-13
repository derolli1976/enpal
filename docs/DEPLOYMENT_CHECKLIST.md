# Deployment Checklist für Home Assistant

## 📋 Vor dem Deployment

### 1. Dateien prüfen
Stelle sicher, dass alle Dateien vorhanden sind:

```
custom_components/enpal_webparser/
├── __init__.py              ✓ Migration Logic
├── config_flow.py           ✓ Data Source Auswahl
├── sensor.py                ✓ Client Factory
├── manifest.json            ✓ Dependencies
├── const.py                 ✓ Konstanten
├── utils.py                 ✓ HTML Parser
├── entity_factory.py        ✓ Entity Erstellung
├── wallbox_api.py           ✓ Wallbox API Client
├── button.py                ✓ Wallbox Buttons
├── switch.py                ✓ Wallbox Switches
├── select.py                ✓ Wallbox Mode Select
├── discovery.py             ✓ Network Discovery
├── models.py                ✓ Data Models
├── api/
│   ├── __init__.py          ✓ API Exports
│   ├── base.py              ✓ Abstract Base Class
│   ├── websocket_client.py  ✓ WebSocket Implementation
│   ├── websocket_parser.py  ✓ JSON → Sensor Parser
│   ├── html_client.py       ✓ HTML Wrapper
│   └── protocol.py          ✓ Blazor SignalR Protocol
├── translations/
│   ├── en.json              ✓ Englische Übersetzungen
│   └── de.json              ✓ Deutsche Übersetzungen
├── tests/                   (Optional - nicht für Deployment nötig)
└── icons/                   (Optional)
```

### 2. Dependencies prüfen
Prüfe `manifest.json`:
```json
{
  "requirements": [
    "beautifulsoup4>=4.11.1",
    "aiohttp>=3.8.0",
    "msgpack>=1.0.0",
    "psutil>=5.9.0"
  ]
}
```

## 🚀 Deployment-Optionen

### Option 1: PowerShell Script (Empfohlen)
```powershell
.\deploy_to_homeassistant.ps1
```

Das Script:
- ✓ Fragt nach HA-Pfad
- ✓ Erstellt automatisch Backup
- ✓ Kopiert alle Dateien
- ✓ Prüft ob alle wichtigen Dateien vorhanden
- ✓ Optional: Startet HA neu

### Option 2: Manuell
```powershell
# 1. Backup erstellen (falls Integration existiert)
$haPath = "C:\Users\<user>\AppData\Roaming\.homeassistant"
$targetPath = "$haPath\custom_components\enpal_webparser"

if (Test-Path $targetPath) {
    $backup = "$targetPath.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item -Path $targetPath -Destination $backup -Recurse
}

# 2. Alte Version löschen
Remove-Item -Path $targetPath -Recurse -Force -ErrorAction SilentlyContinue

# 3. Neue Version kopieren
Copy-Item -Path "custom_components\enpal_webparser" -Destination $targetPath -Recurse

# 4. Home Assistant neu starten
```

## 🧪 Testing nach Deployment

### Test 1: Migration bestehender Config
**Erwartung**: Bestehende Integration läuft ohne Änderungen weiter

```
1. Home Assistant starten
2. Logs prüfen:
   [Enpal] Migrating existing config - setting data_source to 'html'
3. Sensoren sollten wie gewohnt funktionieren
4. Keine Breaking Changes!
```

### Test 2: Auto-Detection (Neue Installation)
**Erwartung**: WebSocket wird automatisch erkannt

```
1. Settings → Devices & Services → Add Integration
2. "Enpal" suchen und hinzufügen
3. Discovery: Enpal Box auswählen
4. Configure: Data Source auf "Auto-detect" lassen
5. Log prüfen:
   [Enpal] Testing WebSocket support for http://192.168.x.x
   [Enpal] WebSocket connection successful
   [Enpal] Auto-detected data source: websocket
6. Integration erstellt → Sensoren sollten mit WebSocket laufen
```

### Test 3: Manuelle WebSocket-Auswahl
**Erwartung**: WebSocket wird verwendet

```
1. Bestehende Integration: Settings → Devices & Services → Enpal → Configure
2. Data Source auf "WebSocket (real-time)" ändern
3. Speichern
4. Log prüfen:
   [Enpal] Using WebSocket client
   [Enpal] Fetched 106 sensors from websocket
```

### Test 4: HTML Fallback
**Erwartung**: Fällt zurück auf HTML wenn WebSocket nicht verfügbar

```
1. WebSocket auswählen (auf Box ohne WebSocket-Support)
2. Log prüfen:
   [Enpal] WebSocket selected but not available, falling back to HTML
   [Enpal] Using HTML client
```

## 📊 Logs zum Debuggen

### Wichtige Log-Nachrichten:

#### Bei Start:
```
[Enpal] async_setup_entry started for entry_id: <id>
[Enpal] Configuration - URL: ..., Data Source: websocket
[Enpal] Using WebSocket client
```

#### Bei Migration:
```
[Enpal] Migrating existing config - setting data_source to 'html'
```

#### Bei WebSocket-Verbindung:
```
[Enpal] Testing WebSocket support for http://192.168.x.x
[Enpal] WebSocket connection successful
[Enpal] Connected to Enpal Box via WebSocket
```

#### Bei Daten-Abruf:
```
[Enpal] Fetched 106 sensors from websocket
[Enpal] Verfügbare Sensoren nach HTML-Parsing:
```

#### Bei Fehlern:
```
[Enpal] Error during update, using last known good values: <error>
[Enpal] WebSocket selected but not available, falling back to HTML
```

### Log-Befehle:

```powershell
# Alle Logs ansehen (Live)
Get-Content "$haPath\home-assistant.log" -Tail 100 -Wait

# Nur Enpal-Logs
Get-Content "$haPath\home-assistant.log" | Select-String -Pattern "\[Enpal\]"

# Letzte 50 Enpal-Logs
Get-Content "$haPath\home-assistant.log" | Select-String -Pattern "\[Enpal\]" | Select-Object -Last 50

# Fehler suchen
Get-Content "$haPath\home-assistant.log" | Select-String -Pattern "\[Enpal\].*error" -CaseSensitive:$false
```

## ⚠️ Bekannte Probleme & Lösungen

### Problem 1: "Integration can't be loaded"
**Lösung**: Dependencies fehlen
```
# HA Terminal oder SSH:
pip install msgpack aiohttp beautifulsoup4 psutil
```

### Problem 2: "WebSocket connection failed"
**Lösung**: Enpal Box nicht erreichbar oder kein WebSocket-Support
- Automatischer Fallback auf HTML sollte funktionieren
- Log prüfen auf "falling back to HTML"

### Problem 3: Sensoren werden nicht erstellt
**Lösung**: 
1. Logs prüfen auf Fehler
2. Sicherstellen dass Enpal Box erreichbar ist
3. Gruppen in Config prüfen

### Problem 4: "api_client.close() failed"
**Lösung**: Ist nur Warning beim Beenden, kein kritischer Fehler

## ✅ Success Indicators

Die Integration läuft erfolgreich wenn:

1. ✓ Keine Errors in Logs
2. ✓ Migration-Message erscheint (bei bestehender Config)
3. ✓ "Using WebSocket client" oder "Using HTML client" im Log
4. ✓ "Fetched X sensors" Nachricht
5. ✓ Sensoren erscheinen in HA
6. ✓ Sensor-Werte aktualisieren sich

## 🎯 Performance Vergleich

Nach erfolgreichem Deployment kannst du die Performance vergleichen:

| Metrik | HTML | WebSocket |
|--------|------|-----------|
| Latenz | ~2-3s | ~200ms |
| Update-Frequenz | Poll-basiert (60s default) | Push (Echtzeit) |
| Netzwerk-Last | Hoch | Niedrig |
| Server-Last | Hoch | Niedrig |

## 📞 Support

Bei Problemen:
1. Logs sammeln (siehe oben)
2. GitHub Issue erstellen mit:
   - Log-Auszüge mit [Enpal] Nachrichten
   - Home Assistant Version
   - Enpal Box Modell/Generation
   - Data Source (websocket/html)
   - Fehlerbeschreibung

---

## Quick Start

```powershell
# 1. Deployment
.\deploy_to_homeassistant.ps1

# 2. HA neu starten

# 3. Logs prüfen
Get-Content "$env:APPDATA\.homeassistant\home-assistant.log" | Select-String -Pattern "\[Enpal\]" | Select-Object -Last 20

# 4. Fertig! 🎉
```

Viel Erfolg! 🚀
