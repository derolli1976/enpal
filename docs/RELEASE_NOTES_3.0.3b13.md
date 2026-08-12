# 3.0.3b13 - Firmware 8.51 (Beta)

Diese Beta schließt die Lücke, die in b12 noch ~45 Sensoren auf "nicht verfügbar" ließ (Rückmeldung von @Graib, Danke!). Betroffen waren vor allem Huawei-Anlagen: SOC pro Batterie-Einheit, Batterietemperatur (Raw), String-Spannungen mit Herstellersuffix und weitere versteckte Werte.

---

## ⚠️ Beta-Version

> Diese Version ist zum Testen gedacht.
>
> - 💾 Vor der Installation ein Home Assistant-Backup anlegen.
> - 🔄 Bei Problemen kannst du über HACS jederzeit auf 3.0.2 zurückwechseln.
> - 🐛 Auffälligkeiten bitte in [Issue #148](https://github.com/derolli1976/enpal/issues/148) melden.

---

## 🐛 Behobene Fehler

### Sensoren mit unbekannten Keys wurden vor der Verarbeitung verworfen

b12 hat die Zeilen des großen Seiten-Renders nur dann ausgewertet, wenn der Sensor-Key in der internen Zuordnungstabelle stand. Die Tabelle wurde aus einer FoxESS-Anlage befüllt. Huawei-spezifische Keys wie `Energy.Battery.Charge.Level.Unit.1`, `Battery.Temperature.Raw` oder `Voltage.String.1.Huawei` fehlten darin und wurden verworfen, bevor der "Uncategorized"-Auffangmechanismus greifen konnte. Solche Sensoren tauchten nur auf, wenn sich ihr Wert zufällig änderte.

Die Zeilenerkennung arbeitet jetzt mit dem Muster der Sensor-Keys statt mit einer festen Liste. Jede Zeile der Seite wird ausgewertet, egal ob der Key bekannt ist. Unbekannte Keys landen wie in b12 unter "Uncategorized". Gegen die Mitschnitte aller drei bekannten Anlagentypen (Huawei 8.50, Huawei 8.51, FoxESS 8.51) geprüft: keine Geister-Sensoren, keine Duplikate.

### Historische Huawei-Keys wieder den richtigen Gruppen zugeordnet

Zwölf Keys aus den 8.50-Mitschnitten von Huawei-Anlagen sind jetzt mit ihren damaligen Gruppen in der Zuordnungstabelle (u. a. `Power.AC.Max`, `Voltage.String.1/2.Huawei`, `Battery.Temperature.Raw`, `Power.AC.Total.Calculated`, `IoTDevice.HealthResponse.Json`, die Heatpump-Werte). Diese Sensoren beleben ihre alten Entity-IDs wieder, statt neue "Uncategorized"-Duplikate anzulegen.

## 📋 Bekannte Einschränkungen

- `Setting.Charge.From.Grid` stand unter 8.50 in zwei Karten gleichzeitig und bleibt bewusst ohne feste Zuordnung; der Wert erscheint als "Uncategorized"-Sensor.
- `SoftwareVersion.Service.2.Fox` (FoxESS) erscheint ebenfalls als "Uncategorized"-Sensor (steht auf der Seite in zwei Karten).
- Zeilen ohne Messwert (Notiz "invalid" oder "missing") werden übersprungen. Der Sensor behält seinen letzten bekannten Wert.

## 🙏 Bitte an die Tester

Falls nach b13 weiterhin Sensoren fehlen: bitte ein Debug-Log anhängen (Einstellungen → Geräte & Dienste → Enpal Solar → Debug-Protokollierung aktivieren, 5 Minuten warten). Wichtig ist die Zeile `Enabled page toggle 'show...'` — sie bestätigt, dass die versteckten Werte auf deiner Box eingeschaltet wurden.
