# 2.2.1 - Fehlende Stromsensoren ergänzt

## 🐞 Fix

**Stromsensoren wieder verfügbar**: Bei manchen Enpal-Anlagen werden die PowerSensor-Stromsensoren (Phase A, B, C) nicht mehr bereitgestellt. Die Integration berechnet diese nun automatisch aus den vorhandenen Leistungs- und Spannungswerten.

Die drei Sensoren erscheinen nach dem Update automatisch:
- `sensor.powersensor_current_phase_a`
- `sensor.powersensor_current_phase_b`  
- `sensor.powersensor_current_phase_c`

**Zukunftssicher**: Sollte Enpal die Sensoren später wieder bereitstellen, erkennt die Integration das automatisch und verhindert Duplikate.

## � Update-Hinweise

Auf 2.2.1 aktualisieren und Home Assistant neu starten (wichtig: nicht nur Integration neu laden).

Nach dem Neustart erscheinen die drei Stromsensoren automatisch – keine weitere Konfiguration erforderlich.

## ℹ️ Kompatibilität

Keine Breaking Changes. Alle bestehenden Sensoren und historischen Daten bleiben unverändert.

## 🙏 Danke

Danke für die Fehlerberichte zu den fehlenden Stromsensoren!

Feedback, Verbesserungsvorschläge oder Fehlermeldungen können auf [GitHub](https://github.com/derolli1976/enpal) oder in den Diskussionen gemeldet werden.
