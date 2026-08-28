# 3.2.0b2 - System-Status auch für Sungrow-Anlagen (Issue #180)

Dieses Beta-Release behebt den nicht verfügbaren Inverter-System-Status auf Sungrow-Anlagen und löst die einzelnen Status-Bits jetzt herstellerspezifisch auf.

---

## 🐛 Fix: Inverter-Status auf Sungrow-Anlagen (Issue #180)

### Das Problem

Auf Sungrow-Anlagen mit Firmware 8.51 blieben `sensor.inverter_system_state` und alle abgeleiteten Status-Sensoren (Decimal, Flags, einzelne Bits) dauerhaft "nicht verfügbar".

Die Ursache: Sungrow liefert das Status-Bitfeld unter einem anderen Datenpunkt als Huawei. Bei Huawei steht es in `Inverter.System.State`, bei Sungrow in `Inverter.Running.State`. `Inverter.System.State` enthält bei Sungrow nur einen kurzen Text wie "Running (64)". Die Integration hat das Bitfeld bisher fest am Huawei-Datenpunkt gesucht. Der kurze Sungrow-Wert wurde dabei verworfen, das eigentliche Bitfeld nie ausgewertet.

### Der Fix

Die Erkennung hängt nicht mehr am Namen des Datenpunkts, sondern am Inhalt. Egal unter welchem Schlüssel das Bitfeld ankommt, es wird erkannt und in die bekannten Einzelsensoren zerlegt.

- `sensor.inverter_system_state` zeigt bei Sungrow jetzt den Klartext-Status (z. B. "Running (64)").
- `sensor.inverter_running_state` führt das Bitfeld als eigenen Basissensor.
- Die Einzelsensoren (Decimal, Flags, Bits) werden wie gewohnt erzeugt.

## ✨ Neu: Herstellerspezifische Status-Bits

Die Bedeutung der einzelnen Status-Bits war bisher fest auf Huawei-Wechselrichter zugeschnitten. Ein Sungrow-Bit wie "PV power generated" wurde als "Standby" beschriftet.

Jetzt liest die Integration die Bit-Beschriftungen direkt aus den Daten der Box. Sungrow-Anlagen bekommen damit korrekte Sensoren:

- `sensor.inverter_system_state_pv_power_generated`
- `sensor.inverter_system_state_battery_charging`
- `sensor.inverter_system_state_battery_discharging`
- `sensor.inverter_system_state_positive_load_power`
- `sensor.inverter_system_state_feed_in_power`
- `sensor.inverter_system_state_importing_power`

Alle neuen Sensoren haben passende Icons.

**Hinweis für Sungrow-Nutzer:** Die alten, falsch beschrifteten Bit-Sensoren (z. B. `sensor.inverter_system_state_standby`) werden nicht mehr befüllt und können in Home Assistant gelöscht werden.

**Huawei-Anlagen sind nicht betroffen:** Alle bestehenden Entity-IDs bleiben unverändert, Historie und Automationen funktionieren weiter.

## 🧪 Beta-Hinweis

Der Fix wurde gegen aufgezeichnete Daten einer Sungrow-Anlage (SH10RT-20, Firmware 8.51.1) und die bekannten Huawei- und FoxESS-Testdaten validiert. Rückmeldungen von Sungrow-Systemen sind willkommen, am besten als [GitHub Issue](https://github.com/derolli1976/enpal/issues).

## 🔄 Kompatibilität

- Keine Änderungen an bestehenden Entity-IDs auf Huawei- und FoxESS-Anlagen
- WebSocket-, HTML- und InfluxDB-Modus bleiben ansonsten unverändert
- Enthält die InfluxDB-Datenquelle aus 3.2.0b1 und alle Fixes aus 3.1.2

## ❤️ Unterstützung

Wenn dir die Integration hilft und du die Weiterentwicklung unterstützen möchtest, freue ich mich über eine Spende über die **Sponsoring-Sektion** dieses Repositories (Button "Sponsor" oben auf der [Projektseite](https://github.com/derolli1976/enpal)) oder über [Buy Me a Coffee](https://buymeacoffee.com/derolli1976). Danke!
