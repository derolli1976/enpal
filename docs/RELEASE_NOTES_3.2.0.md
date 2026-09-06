# 3.2.0 - Neue Datenquelle InfluxDB und System-Status für Sungrow-Anlagen

Dieses Release bringt eine dritte Datenquelle: Die Integration kann die Messwerte direkt aus der InfluxDB der Enpal Box lesen. Außerdem funktioniert der Inverter-System-Status jetzt auch auf Sungrow-Anlagen (Issue #180).

Das Release fasst die Beta-Versionen 3.2.0b1 und 3.2.0b2 zusammen.

---

## ✨ Neu: Datenquelle InfluxDB (Experten-Option)

### Was es bringt

Der InfluxDB-Modus liest die Werte direkt aus der Datenbank der Box, nicht aus der Weboberfläche. Er ist damit unabhängig von den Umbauten, die Enpal an der Webseite vornimmt. Die Firmware-Updates 8.50 und 8.51 haben gezeigt, wie oft solche Umbauten die Integration treffen können.

- Gleiche Entity-IDs wie im WebSocket-Modus. Ein Wechsel der Datenquelle erzeugt keine neuen Entitäten, Historie und Automationen bleiben erhalten.
- Einheiten kommen sauber aus der Datenbank (inklusive Wh-zu-kWh-Umrechnung wie bisher).
- Die Wallbox wird wie im WebSocket-Modus nativ gesteuert, ohne Add-on.
- Abfrage im eingestellten Intervall über eine einzelne Datenbank-Query. Keine zusätzlichen Abhängigkeiten.

### Was du brauchst

1. Öffne ein Ticket über den **Enpal Chatbot in der Enpal App** und frage den **InfluxDB-Zugriffstoken** und die **Organisation** für deine Box an.
2. Wähle im Setup oder in den Optionen der Integration die Datenquelle **"InfluxDB (expert, token required)"** und speichere.
3. Trage in den neu erscheinenden Feldern den Token ein. Organisation (`enpal`) und Bucket (`solar`) sind vorbelegt und passen in der Regel.

Die Integration prüft die Verbindung beim Speichern und zeigt eine verständliche Fehlermeldung, wenn Token oder Organisation nicht stimmen.

### Einschränkungen

- Die Datenbank enthält nur Zahlenwerte. Textsensoren wie Seriennummern oder Gerätenamen gibt es in diesem Modus nicht. Der Wallbox-Status kommt weiterhin über die Weboberfläche der Box.
- Der System-Status des Inverters liegt in der Datenbank nur als Zahl vor. Die Integration leitet die bekannten Einzelsensoren (Decimal, Flags, einzelne Bits) daraus ab.
- Die automatische Erkennung der Datenquelle wählt InfluxDB nie von selbst. Der Modus ist eine bewusste Entscheidung.

### Warum "Experten-Option"?

Der Modus braucht einen Token, den du aktiv bei Enpal anfragen musst. Genau daran sind früher viele Setups gescheitert, deshalb war der InfluxDB-Zugriff bisher bewusst nicht eingebaut. Wer den Token hat, bekommt jetzt einen robusten dritten Weg.

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

## 🧪 Getestet

- InfluxDB-Modus: Live gegen eine Box mit Firmware Solar Rel. 8.51.1 und InfluxDB 2.8.0 (Huawei-System, 124 Sensoren)
- Sungrow-Fix: Gegen aufgezeichnete Daten einer Sungrow-Anlage (SH10RT-20, Firmware 8.51.1) und die bekannten Huawei- und FoxESS-Testdaten
- Beta-Phase 3.2.0b1/b2 ohne weitere Fehlermeldungen abgeschlossen

## 🔄 Kompatibilität

- Keine Änderungen an bestehenden Entity-IDs auf Huawei- und FoxESS-Anlagen
- WebSocket- und HTML-Modus bleiben unverändert
- Enthält alle Fixes aus 3.1.2

## ❤️ Unterstützung

Wenn dir die Integration hilft und du die Weiterentwicklung unterstützen möchtest, freue ich mich über eine Spende über die **Sponsoring-Sektion** dieses Repositories (Button "Sponsor" oben auf der [Projektseite](https://github.com/derolli1976/enpal)) oder über [Buy Me a Coffee](https://buymeacoffee.com/derolli1976). Danke!
