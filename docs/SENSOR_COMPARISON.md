# Sensor-Vergleich: HTML vs. WebSocket

**Stand:** 26. Dezember 2024  
**Übereinstimmung:** 66.2% (88 von 133 HTML-Sensoren)

## Zusammenfassung

| Kategorie | Anzahl | Beschreibung |
|-----------|--------|--------------|
| **In beiden** | 88 | Core-Sensoren, die in beiden Modi verfügbar sind |
| **Nur HTML** | 45 | Detaillierte Konfiguration und einzelne Unit-Daten |
| **Nur WebSocket** | 18 | Aggregierte Werte und Source-Tracking |
| **HTML Gesamt** | 133 | Alle Sensoren im HTML-Modus |
| **WebSocket Gesamt** | 106 | Alle Sensoren im WebSocket-Modus |

## Unterschiede nach Gruppen

### Battery

| Status | Anzahl | Beispiele |
|--------|--------|-----------|
| ✅ In beiden | ~13 | `Current.Battery`, `Power.Battery.Charge`, `Temperature.Battery` |
| 🔴 Nur HTML | 25 | Battery Unit Details, ChargeLevel Min/Max, Running States |
| 🟢 Nur WebSocket | 0 | - |

#### Nur in HTML (Battery)
- `Battery.ChargeLevel.Max` / `.Min` - Min/Max Ladezustand
- `Battery.Running.State.Unit.1` / `.Unit.2` - Status einzelner Units
- `Current.Battery.Unit.1` / `.Unit.2` - Strom pro Unit
- `Voltage.Battery.Unit.1` / `.Unit.2` - Spannung pro Unit
- `Energy.Battery.Charge.Level.Unit.1` / `.Unit.2` - Ladestand pro Unit
- `SerialNumber.Battery.Unit.1` - Seriennummern
- `SoftwareVersion.Service.Battery.Unit.1` - Firmware-Versionen
- `Battery.Force.ChargeDisCharge.Mode` - Erzwungene Lade-/Entlade-Modi
- `Mode.Battery.Working` - Betriebsmodus
- `Mode.Forcible.Charge.Discharge` - Konfigurationsparameter
- `Duration.Battery.Force.ChargeDisCharge` - Dauer erzwungener Modi
- `Storage.Power.Of.Charge.From.Grid` - Netzbezug-Konfiguration
- `Setting.Charge.From.Grid` - Netzladung aktiviert/deaktiviert
- `Grid.Charge.Cutoff.SOC` - Netzladung Abschalt-SOC

### Inverter

| Status | Anzahl | Beispiele |
|--------|--------|-----------|
| ✅ In beiden | ~28 | `Current.String.1`, `Energy.Battery.Charge.Lifetime`, `Power.AC.L1` |
| 🔴 Nur HTML | 20 | Calculated vs Huawei Values, Alarm Codes, Config |
| 🟢 Nur WebSocket | 2 | `Energy.Consumption.Total.Day`, `Power.House.Total` |

#### Nur in HTML (Inverter)
- `State.AlarmCodes.1` / `.2` / `.3` - Alarm-Codes
- `SerialNumber` - Seriennummer
- `Inverter.Running.State` - Betriebszustand
- `Power.DC.Total.Calculated` vs `.Huawei` - Berechnete vs. Huawei-Werte
- `Power.Grid.Export.Huawei` - Huawei-spezifischer Exportwert
- `Grid.Import.Power.Total.Calculated` - Berechneter Import
- `Inverter.Power.Total` - Gesamtleistung
- `Power.Battery.Charge.Max` / `.Discharge.Max` - Max Lade-/Entladeleistung
- `Power.Battery.Charge.Discharge` - Aktuelle Lade-/Entladeleistung
- `Power.Active.Fixed` - Feste Wirkleistung
- `Power.Reactive` - Blindleistung
- `Power.Factor` - Leistungsfaktor
- `Mode.Power.Active` - Wirkleistungsmodus
- `Mode.Forcible.Charge.Discharge` - Erzwungener Modus
- `Setting.Charge.From.Grid` - Netzladung-Einstellung
- `Power.AC.Max` - Max AC-Leistung

#### Nur in WebSocket (Inverter)
- `Energy.Consumption.Total.Day` - Tagesverbrauch (aggregiert)
- `Power.House.Total` - Gesamthaus-Leistung (aggregiert)

### IoTEdgeDevice

| Status | Anzahl | Beispiele |
|--------|--------|-----------|
| ✅ In beiden | 25 | `Cpu.Load`, `IoT.Data.Consumption.Lan.Down.Month`, `LTE.Failover.Result` |
| 🔴 Nur HTML | 0 | - |
| 🟢 Nur WebSocket | 0 | - |

**100% Übereinstimmung** - Alle IoTEdgeDevice-Sensoren sind identisch!

### PowerSensor

| Status | Anzahl | Beispiele |
|--------|--------|-----------|
| ✅ In beiden | 6 | `Power.AC.Phase.A/B/C`, `Voltage.Phase.A/B/C` |
| 🔴 Nur HTML | 0 | - |
| 🟢 Nur WebSocket | 0 | - |

**100% Übereinstimmung** - Alle PowerSensor-Sensoren sind identisch!

### Site Data

| Status | Anzahl | Beispiele |
|--------|--------|-----------|
| ✅ In beiden | 3 | `Energy.Consumption.Total.Day`, `Energy.Consumption.Total.Lifetime`, `Power.Consumption.Total` |
| 🔴 Nur HTML | 0 | - |
| 🟢 Nur WebSocket | 13 | Produktions-, Speicher- und Netz-Aggregationen |

#### Nur in WebSocket (Site Data)
- `Energy.Production.Total.Day` - Tagesproduktion gesamt
- `Power.Production.Total` - Aktuelle Produktion gesamt
- `Energy.External.Total.In.Day` - Netzbezug heute
- `Energy.External.Total.Out.Day` - Netzeinspeisung heute
- `Power.External.Total` - Aktuelle Netzleistung
- `Energy.Storage.Total.In.Day` - Speicherladung heute
- `Energy.Storage.Total.Out.Day` - Speicherentladung heute
- `Power.Storage.Total` - Aktuelle Speicherleistung
- `Energy.Storage.Level` - Absoluter Speicherstand (kWh)
- `Percent.Storage.Level` - Speicherstand (%)

**Vorteil WebSocket:** Umfassende Aggregationen für Energieflüsse!

### Wallbox

| Status | Anzahl | Beispiele |
|--------|--------|-----------|
| ✅ In beiden | 14 | `Current.Wallbox.Connector.1.Phase.A/B/C`, `Energy.Wallbox.Connector.1.Charged.Total` |
| 🔴 Nur HTML | 0 | - |
| 🟢 Nur WebSocket | 6 | Source-Tracking (Batterie/Netz/Solar) |

#### Nur in WebSocket (Wallbox)
- `Energy.Wallbox.Connector.1.byBattery.Total` - Ladung aus Batterie gesamt
- `Energy.Wallbox.Connector.1.byGrid.Total` - Ladung aus Netz gesamt
- `Energy.Wallbox.Connector.1.bySolar.Total` - Ladung aus Solar gesamt
- `Power.Wallbox.Connector.1.byBattery` - Aktuelle Leistung aus Batterie
- `Power.Wallbox.Connector.1.byGrid` - Aktuelle Leistung aus Netz
- `Power.Wallbox.Connector.1.bySolar` - Aktuelle Leistung aus Solar

**Vorteil WebSocket:** Detailliertes Source-Tracking für Wallbox-Ladung!

## Bewertung

### Vorteile HTML-Modus
- ✅ Mehr Sensoren insgesamt (133 vs. 106)
- ✅ Detaillierte Unit-Informationen (Battery Unit 1/2)
- ✅ Alarm-Codes und Fehlermeldungen
- ✅ Berechnete vs. Hersteller-Werte
- ✅ Konfigurationsparameter sichtbar
- ✅ Seriennummern und Firmware-Versionen

### Vorteile WebSocket-Modus
- ✅ Real-time Updates ohne Polling
- ✅ Geringere Netzwerklast
- ✅ Aggregierte Energiefluss-Daten (Production, External, Storage)
- ✅ Wallbox Source-Tracking (Battery/Grid/Solar)
- ✅ Gesamthaus-Verbrauch (Power.House.Total)
- ✅ Speicherstand in kWh und Prozent

### Empfehlung

| Anwendungsfall | Empfohlener Modus | Begründung |
|----------------|-------------------|------------|
| **Standard** | WebSocket | Real-time, effizient, ausreichend Daten |
| **Fehlerbehebung** | HTML | Alarm-Codes, detaillierte States |
| **Entwicklung** | HTML | Alle Konfigurationsparameter sichtbar |
| **Home Assistant Dashboard** | WebSocket | Source-Tracking, Energiefluss-Aggregationen |
| **Monitoring einzelner Units** | HTML | Battery Unit 1/2 Details |

## Kompatibilität beim Wechsel

Beim Wechsel zwischen Modi:
- ✅ **88 Core-Sensoren bleiben identisch** (gleiche Namen dank Dot-Notation)
- ⚠️ **45 HTML-spezifische Sensoren werden unavailable** (Unit Details, Alarm Codes)
- ✅ **18 WebSocket-spezifische Sensoren kommen hinzu** (Aggregationen, Source-Tracking)

### Auswirkungen auf Automationen/Dashboards
- Automationen mit Core-Sensoren: ✅ Keine Änderung nötig
- Automationen mit Alarm-Codes: ⚠️ Funktionieren nur im HTML-Modus
- Dashboards mit Source-Tracking: ⚠️ Funktionieren nur im WebSocket-Modus

---

**Fazit:** Die 66.2% Übereinstimmung sind **sehr gut**! Die Unterschiede sind keine Naming-Probleme, sondern **unterschiedliche Datenverfügbarkeit**. Die identische Dot-Notation ermöglicht nahtlosen Wechsel für alle Core-Sensoren.
