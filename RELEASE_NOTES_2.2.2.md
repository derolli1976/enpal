# 2.2.2 - Multi-Inverter Support für Energiesensor

## 🐞 Fix

**Energiesensor funktioniert jetzt mit allen Inverter-Typen**: Der Sensor `sensor.inverter_energy_produced_total_dc` zeigte bei Nicht-Huawei-Anlagen keine Werte an (Issue #87). Die Integration erkennt nun automatisch den passenden DC-Leistungssensor für alle Inverter-Hersteller.

**Transparenz**: Der Sensor zeigt im Attribut `source_sensor` an, welcher DC-Leistungssensor verwendet wird.

## 🎯 Betroffene Systeme

Besonders wichtig für Anlagen mit Nicht-Huawei-Invertern
Huawei-Anlagen funktionieren weiterhin wie bisher ohne Änderung.

## 📋 Update-Hinweise

Auf 2.2.2 aktualisieren und Home Assistant neu starten (wichtig: nicht nur Integration neu laden).

Nach dem Neustart:
- Der Energiesensor `sensor.inverter_energy_produced_total_dc` sollte nun Werte anzeigen
- Im Attribut `source_sensor` können Sie sehen, welcher Sensor verwendet wird
- Bei Bedarf in den Logs nach `[Enpal]` suchen für Details zur Sensor-Auswahl

## ℹ️ Kompatibilität

Keine Breaking Changes. Alle bestehenden Sensoren und historischen Daten bleiben unverändert.

**Rückwärtskompatibel**: Huawei-Anlagen nutzen weiterhin den optimierten Huawei-Sensor.

## 🧪 Getestet mit

- Huawei Invertern (Priorität 1)
- Generic DC Total Sensor

## 🙏 Danke

Danke für die Fehlermeldung zu Issue #87 und das bereitgestellte HTML von @fabfive für Tests!

Feedback, Verbesserungsvorschläge oder Fehlermeldungen können auf [GitHub](https://github.com/derolli1976/enpal) oder in den Diskussionen gemeldet werden.
