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

### Gruppenauswahl blendet nur noch aus, statt zu filtern

Bisher hat die Integration abgewählte Gerätegruppen komplett ignoriert. Tauchte eine neue Gruppe auf (wie jetzt "ControlBox") oder verschob Enpal Sensoren in eine andere Gruppe, fehlten die Werte, bis man die Optionen anpasste.

Ab dieser Version werden immer alle Gruppen gelesen. Die Auswahl in den Optionen bestimmt nur noch, ob die Entities einer Gruppe in Home Assistant standardmäßig aktiviert sind. Abgewählte Gruppen erzeugen deaktivierte Entities, die sich jederzeit einzeln einschalten lassen. Neue Gruppen, die es zum Zeitpunkt deiner Konfiguration noch nicht gab, sind automatisch aktiv.

Sensor-Keys, die die Integration noch keiner Gruppe zuordnen kann, werden ab jetzt unter der Gruppe "Uncategorized" angelegt statt verworfen. Der Wert ist damit sofort verfügbar. Hinweis: Wird der Key in einer späteren Version einer richtigen Gruppe zugeordnet, entsteht eine neue Entity-ID.

### Neue Gerätegruppe "ControlBox"

Neuere Anlagen (z. B. mit FoxESS-Wechselrichter und Starcharge-Wallbox) haben eine zusätzliche Karte "ControlBox" mit EEBUS- und Smart-Meter-Gateway-Werten. Die Gruppe ist jetzt bekannt, in den Standardgruppen enthalten und bei bestehenden Installationen automatisch aktiv.

### Über 100 neue Sensor-Zuordnungen

Die Tabelle, die Sensor-Keys ihren Gerätegruppen zuordnet, wurde um die Werte einer FoxESS-Anlage mit Firmware 8.51 erweitert (u. a. `Battery.SOH`, `Power.DC.String.3` bis `.6`, EEBUS-Status, Fehlercodes). Die Zuordnung wurde gegen die Data-Collector-Ausgabe der Box gegengeprüft.

## 📋 Bekannte Einschränkungen

- Drei Keys stehen auf der Seite in zwei Karten gleichzeitig (`Energy.Consumption.Total.Lifetime`, `Power.AC.Max`, `SoftwareVersion.Service.2.Fox`). Über den WebSocket-Pfad entsteht dafür ein einzelner "Uncategorized"-Sensor; welcher der beiden Kartenwerte dort steht, kann wechseln.
- Zeilen ohne Messwert (Notiz "invalid" oder "missing") werden übersprungen. Der Sensor behält seinen letzten bekannten Wert.
