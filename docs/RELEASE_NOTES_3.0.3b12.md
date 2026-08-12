# 3.0.3b12 - Firmware 8.51 (Beta)

Diese Beta bringt die unter Firmware **Solar Rel. 8.51** ausgeblendeten Werte zurück, darunter den Batterie-Ladestand (SOC), die Batterietemperatur und die Batteriespannung.

Möglich wurde das durch den direkten Zugang zur Box eines Users (Danke!). Der Vergleich mit einem echten Browser hat die Ursache der fehlgeschlagenen Schalter-Klicks aus den Betas b7 bis b10 exakt eingegrenzt.

---

## ⚠️ Beta-Version

> Diese Version ist zum Testen gedacht.
>
> - 💾 Vor der Installation ein Home Assistant-Backup anlegen.
> - 🔄 Bei Problemen kannst du über HACS jederzeit auf 3.0.2 zurückwechseln.
> - 🐛 Auffälligkeiten bitte in [Issue #148](https://github.com/derolli1976/enpal/issues/148) melden.

---

## 🐛 Behobene Fehler

### Ausgeblendete Werte (SOC, Batterietemperatur) sind zurück

Firmware 8.51 verbirgt einen Teil der Werte hinter den Checkboxen "Show unsupported values" und "Show internal values". Die Integration schaltet diese Checkboxen jetzt erfolgreich auf ihrer eigenen Verbindung ein und empfängt danach auch die verborgenen Zeilen.

Die Ursache der bisher fehlgeschlagenen Klicks war ein einzelnes Feld in der Klick-Nachricht: Die Integration schickte in den Event-Daten zusätzlich `"type": "change"`. Dieses Feld gehört nicht zum erwarteten Format, und die Box lehnt Nachrichten mit unbekannten Feldern ab. Ein echter Browser schickt nur `{"value": true}`. Nach dem Entfernen des Felds akzeptiert die Box jeden Klick. Die Wallbox-Steuerung war nie betroffen, weil Maus-Klicks ein anderes Format verwenden, das dieses Feld erlaubt.

Im Live-Test gegen eine Box mit Firmware 8.51 wurden alle 12 Checkboxen eingeschaltet. Danach standen 171 Sensoren zur Verfügung, darunter:

- `Energy.Battery.Charge.Level` (SOC)
- `Temperature.Battery`
- `Voltage.Battery`
- `Battery.SOH`

### Inverter-Systemstatus wird wieder zerlegt

Firmware 8.51 liefert den Sensor `Inverter.System.State` als HTML-Liste statt als Text. Der Wert ist über 800 Zeichen lang und konnte weder gepatcht noch als Sensor angelegt werden. Die Integration entfernt jetzt die HTML-Auszeichnung und zerlegt den Wert wie unter 8.50 in die bekannten Teilsensoren mit unveränderten Entity-IDs:

- `sensor.inverter_system_state_decimal`
- `sensor.inverter_system_state_flags`
- die einzelnen Statusbits (z. B. `sensor.inverter_system_state_standby`)

## ✨ Neue Funktionen

### Neue Gerätegruppe "ControlBox"

Neuere Anlagen (z. B. mit FoxESS-Wechselrichter und Starcharge-Wallbox) haben eine zusätzliche Karte "ControlBox" mit EEBUS- und Smart-Meter-Gateway-Werten. Die Gruppe ist jetzt bekannt und in den Standardgruppen enthalten. Bestehende Installationen können sie in den Integrationsoptionen zusätzlich auswählen.

### Über 100 neue Sensor-Zuordnungen

Die Tabelle, die Sensor-Keys ihren Gerätegruppen zuordnet, wurde um die Werte einer FoxESS-Anlage mit Firmware 8.51 erweitert (u. a. `Battery.SOH`, `Power.DC.String.3` bis `.6`, EEBUS-Status, Fehlercodes). Die Zuordnung wurde gegen die Data-Collector-Ausgabe der Box gegengeprüft.

## 📋 Bekannte Einschränkungen

- Drei Keys sind auf der Seite mehrdeutig und werden bewusst nicht automatisch angelegt: `Energy.Consumption.Total.Lifetime` (steht auch unter Site Data), `Power.AC.Max`, `SoftwareVersion.Service.2.Fox`.
- Zeilen ohne Messwert (Notiz "invalid" oder "missing") werden übersprungen. Der Sensor behält seinen letzten bekannten Wert.
