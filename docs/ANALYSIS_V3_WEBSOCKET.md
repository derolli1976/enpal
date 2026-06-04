# Analyse: Enpal WebSocket API für Version 3.0

## 🔍 Was @arigon entwickelt hat

Der User @arigon hat das **Blazor SignalR WebSocket-Protokoll** der Enpal Box reverse-engineered und eine Go-Library entwickelt. Statt HTML-Scraping nutzt diese Library die **native API** der Enpal Box.

## 📊 Technischer Vergleich

### Aktueller Ansatz (v2.x - HTML Parsing)
```
Home Assistant → HTTP GET /deviceMessages → HTML parsen → BeautifulSoup → Sensoren
```

**Vorteile**:
- ✅ Einfach zu verstehen
- ✅ Funktioniert mit allen Enpal Boxen der 1. Generation
- ✅ Keine komplexe Protokoll-Implementierung

**Nachteile**:
- ❌ HTML-Struktur kann sich ändern
- ❌ Kein Echtzeit-Streaming
- ❌ Polling notwendig (Last auf Enpal Box)
- ❌ Begrenzt auf das, was im HTML steht

### Neuer Ansatz (v3.0 - WebSocket API)
```
Home Assistant → WebSocket /\_blazor → Blazor SignalR → MessagePack → JSON → Sensoren
```

**Vorteile**:
- ✅ **Native API** - stabiler als HTML-Scraping
- ✅ **Echtzeit-Updates** via WebSocket Push
- ✅ **Strukturierte Daten** (JSON statt HTML)
- ✅ **Geringere Last** - persistente Verbindung statt Polling
- ✅ **Mehr Daten** - API gibt mehr Details als HTML
- ✅ **Device Classes** direkt im JSON (Inverter, Battery, Wallbox, etc.)

**Nachteile**:
- ⚠️ Komplexere Implementierung
- ⚠️ Abhängig von Blazor-Protokoll
- ⚠️ Nicht dokumentierte API (kann sich ändern)

## 🔧 Technische Details des WebSocket-Protokolls

### Ablauf der WebSocket-Verbindung

1. **HTTP GET** `/collector` → HTML mit Blazor-Komponenten
2. **HTTP POST** `/_blazor/negotiate` → Connection Token
3. **WebSocket** `ws://.../_blazor?id=<token>` → Persistente Verbindung
4. **Handshake** → `{"protocol":"blazorpack","version":1}`
5. **StartCircuit** → Blazor-Circuit initialisieren
6. **UpdateRootComponents** → UI-Komponenten registrieren
7. **Button Click** → Event senden (EventHandler ID 4)
8. **Daten empfangen** → JSON via MessagePack

### Message Format

**MessagePack-kodierte Arrays**:
```go
[msgType, headers, invocationId, target, args]
```

Beispiel Button-Click:
```go
[1, {}, nil, "BeginInvokeDotNetFromJS", [
    "1", nil, "DispatchEventAsync", 1, 
    {"eventHandlerId": 4, "eventName": "click", ...}
]]
```

### Datenstruktur (JSON Response)

```json
{
  "collectionId": "abc123...",
  "ioTDeviceId": "ENPAL-...",
  "timeStampUtc": "2025-12-26T10:30:00Z",
  "deviceCollections": [
    {
      "deviceId": "INV-001",
      "deviceClass": "Inverter",
      "numberDataPoints": {
        "Power.DC.Total": {
          "value": 4500.0,
          "unit": "W",
          "timeStampUtcOfMeasurement": "..."
        }
      },
      "textDataPoints": {...}
    },
    {
      "deviceClass": "Battery",
      ...
    }
  ],
  "energyManagement": [...],
  "errorCodes": [...]
}
```

## 🐍 Python-Portierung

### Benötigte Dependencies

```python
# Bestehend:
- aiohttp (WebSocket Support)
- BeautifulSoup4 (für initiales HTML-Parsing der Blazor-Komponenten)

# Neu:
- msgpack (MessagePack encoding/decoding)
- re (Regex für Blazor-Komponenten-Extraktion)
```

### Architektur-Vorschlag für v3.0

```
custom_components/enpal_webparser/
├── __init__.py
├── config_flow.py
├── const.py
├── manifest.json
├── sensor.py
├── api/
│   ├── __init__.py
│   ├── base.py              # Abstrakte Basis-Klasse
│   ├── html_parser.py       # v2.x HTML-Parsing (Legacy)
│   ├── websocket_client.py  # v3.0 WebSocket-Client (NEU)
│   └── data_models.py       # Gemeinsame Datenmodelle
├── utils.py
└── tests/
```

## 🚀 Implementierungsplan für v3.0

### Phase 1: Dual-Mode Support (Rückwärtskompatibel)

1. **Neue Architektur**:
   - Abstrakte `EnpalApiClient` Basis-Klasse
   - `HtmlParserClient` (bestehende Implementierung)
   - `WebSocketClient` (neue Implementierung)

2. **Config Flow Erweiterung**:
   - Option zur Auswahl: "HTML Parsing" oder "WebSocket API"
   - Auto-Detection: Wenn `/collector` erreichbar → WebSocket verfügbar

3. **Sensor Platform**:
   - Bleibt weitgehend unverändert
   - DataUpdateCoordinator nutzt ausgewählten Client

### Phase 2: WebSocket-Client Implementierung

**Kernfunktionen** (Python-Port von Go-Code):

```python
class EnpalWebSocketClient:
    async def connect(self) -> bool
    async def fetch_data(self) -> CollectorData
    async def close(self) -> None
    def is_connected(self) -> bool
```

**Interne Methoden**:
- `_extract_blazor_components()` - Regex-basiert aus HTML
- `_negotiate_connection()` - HTTP POST für Token
- `_websocket_handshake()` - WebSocket + Blazor Protocol
- `_send_start_circuit()` - Circuit initialisieren
- `_send_update_root_components()` - UI registrieren
- `_click_button()` - Event triggern
- `_handle_message()` - MessagePack decoding
- `_parse_collector_data()` - JSON → Python Objects

### Phase 3: Migration & Testing

1. **Unit Tests** mit echten WebSocket-Responses
2. **Integration Tests** gegen echte Enpal Box
3. **Migration Guide** für bestehende Nutzer
4. **Performance-Vergleich** HTML vs. WebSocket

## 💡 Empfehlung

### Kurzfristig (v2.3.x - v2.4.x)
- ✅ HTML-Parsing weiter verwenden
- ✅ Heatpump-Support fertigstellen
- ✅ Stabilität verbessern

### Mittelfristig (v3.0 - Q1/Q2 2026)
- 🎯 **WebSocket-Client implementieren**
- 🎯 **Dual-Mode Support** (HTML + WebSocket)
- 🎯 Migration-Path für User
- 🎯 Performance-Optimierung

### Vorteile einer v3.0 mit WebSocket

1. **Zukunftssicherheit**: Native API ist stabiler als HTML-Scraping
2. **Echtzeit-Daten**: Push statt Polling
3. **Mehr Datenpunkte**: API gibt mehr Informationen
4. **Bessere Performance**: Weniger Last auf Enpal Box
5. **Community-Beitrag**: Nutzt @arigons Research

## 🤝 Zusammenarbeit mit @arigon

### Möglichkeiten:
1. **Code-Sharing**: Go-Code als Referenz für Python-Port
2. **Protokoll-Dokumentation**: Gemeinsame Dokumentation der API
3. **Testing**: Austausch über verschiedene Enpal-Hardware
4. **Issues**: Gemeinsame Bug-Reports bei Protokoll-Änderungen

### Lizenz-Kompatibilität:
- ✅ @arigons Library: **MIT License**
- ✅ Unsere Integration: **MIT License**
- ✅ Portierung nach Python ist erlaubt

## 📝 Nächste Schritte

### Sofort (Diskussion):
1. Mit @arigon Kontakt aufnehmen (GitHub Issue)
2. Interesse an Zusammenarbeit mitteilen
3. Erfahrungen austauschen

### Vorbereitung (v3.0 Planning):
1. Proof-of-Concept: Python WebSocket-Client
2. Performance-Benchmarks
3. Architektur-Design für Dual-Mode
4. Community-Feedback einholen

### Implementierung (v3.0 Development):
1. `websocket_client.py` entwickeln
2. Tests gegen echte Enpal Box
3. Config Flow erweitern
4. Documentation updaten
5. Beta-Testing mit Community

## ⚠️ Risiken & Mitigation

### Risiko 1: Protokoll-Änderungen
**Mitigation**: Dual-Mode behält HTML als Fallback

### Risiko 2: Komplexität
**Mitigation**: Schrittweise Implementierung, gute Tests

### Risiko 3: Hardware-Varianten
**Mitigation**: Community-Testing mit verschiedenen Boxen

### Risiko 4: Enpal-Updates
**Mitigation**: Monitoring + schnelle Fixes, Fallback auf HTML

## 📊 Erwartete Ergebnisse

### Technisch:
- 🎯 50% weniger Netzwerk-Traffic
- 🎯 90% schnellere Daten-Aktualisierung
- 🎯 Mehr verfügbare Sensoren

### User Experience:
- 🎯 Echtzeit-Updates statt Polling-Delay
- 🎯 Stabilere Integration
- 🎯 Zukunftssichere Lösung

---

## 🎯 Fazit

Die WebSocket-API ist der **richtige Weg für v3.0**. Sie bietet:
- ✅ Bessere Performance
- ✅ Mehr Daten
- ✅ Stabilere Basis
- ✅ Echtzeit-Updates

**Empfehlung**: 
1. v2.3.0 mit Heatpump-Support releasen
2. v3.0 mit WebSocket in Q1/Q2 2026 planen
3. Dual-Mode für sanfte Migration
4. Mit @arigon zusammenarbeiten

Die Go-Library von @arigon ist ein **großartiger Beitrag** zur Community und perfekte Basis für unsere v3.0! 🚀
