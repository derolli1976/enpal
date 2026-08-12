# 3.0.3b11 - Firmware 8.51 (Beta)

Diese Beta behebt die Ursache dafür, dass unter Firmware **Solar Rel. 8.51** fast alle Entitäten auf "nicht verfügbar" standen und nur die Gruppe "Site Data" Werte lieferte.

Die Analyse basiert auf zwei vollständigen Sniffer-Mitschnitten von einer Box mit 8.51 (Danke an @Graib) sowie den Rohdaten und Logs aus [Issue #148](https://github.com/derolli1976/enpal/issues/148).

---

## ⚠️ Beta-Version

> Diese Version ist zum Testen gedacht.
>
> - 💾 Vor der Installation ein Home Assistant-Backup anlegen.
> - 🔄 Bei Problemen kannst du über HACS jederzeit auf 3.0.2 zurückwechseln.
> - 🐛 Auffälligkeiten bitte in [Issue #148](https://github.com/derolli1976/enpal/issues/148) melden.

---

## 🐛 Behobene Fehler

### Sensoren nach Neustart dauerhaft "nicht verfügbar"

Unter Firmware 8.51 enthält die HTTP-Antwort von `/deviceMessages` nur noch die Karte "Site Data" mit vier Zeilen. Alle Gerätetabellen (Battery, Inverter, PowerSensor, Wallbox, IoTEdgeDevice) schickt die Box stattdessen etwa zwei Sekunden nach dem Verbindungsaufbau als einen großen Blazor-RenderBatch über den WebSocket.

Die Integration hat diesen Initial-RenderBatch bisher verworfen. Sie hat nur die kleinen Änderungs-Diffs ausgewertet, die die Box danach schickt. Ein Sensor tauchte deshalb erst dann auf, wenn sich sein Wert zufällig änderte. Selten aktualisierte Sensoren kamen nie zurück. Das erklärt die Berichte, dass Sensoren erst nach Minuten oder Stunden zurückkehrten und danach einfroren.

Die Integration liest den Initial-RenderBatch jetzt vollständig aus. Alle in der Standardansicht sichtbaren Sensoren sind damit direkt nach dem Verbindungsaufbau wieder da. Die Änderungs-Diffs halten sie danach wie gewohnt aktuell. In der Wiedergabe der beiden Sniffer-Mitschnitte wächst die Sensorliste unmittelbar von 4 auf 74 Sensoren, der Rest der aufgezeichneten Zeilen trug keinen Messwert (Box ohne LTE-Modul).

### Periodischer Abruf setzte die Sensorliste zurück

Der regelmäßige HTML-Abruf diente bisher als Basis der Sensorliste. Unter 8.51 liefert er nur noch vier Sensoren. Die per WebSocket erzeugten Sensoren werden jetzt bei jedem Abruf übernommen statt verworfen.

## 🔄 Geänderte Funktionen

### Schalter-Klicks für ausgeblendete Werte deaktiviert

Die Betas b7 bis b10 haben versucht, die Checkboxen "Show unsupported values" und "Show internal values" über den WebSocket anzuklicken, um die standardmäßig ausgeblendeten Werte (z. B. `Energy.Battery.Charge.Level`, `Temperature.Battery`) zu erhalten. Die Auswertung aller Mitschnitte zeigt: Kein einziger dieser Klicks wurde von der Box akzeptiert. Jeder Versuch endete mit einer Server-Exception, unabhängig von Handler-ID und Objekt-Referenz.

Die Klicks sind in dieser Beta deaktiviert. Sie brachten keine Daten und erzeugten nur Protokoll-Rauschen. Die ausgeblendeten Werte bleiben vorerst "nicht verfügbar". Wir arbeiten an einer Lösung, sobald der Klick-Mechanismus eines echten Browsers mitgeschnitten und verstanden ist.

## 📋 Bekannte Einschränkungen

- Standardmäßig ausgeblendete Werte (u. a. Batterie-Ladestand, Batterietemperatur, Batteriespannung) fehlen weiterhin. Enpal hat sie unter 8.51 hinter Checkboxen verschoben.
- Der Sensor `Inverter.System.State` wird unter 8.51 nicht angelegt. Die Box liefert ihn in einem neuen HTML-Format, das der Parser noch nicht zerlegt.
- Zeilen ohne Messwert (Notiz "invalid" oder "missing") werden übersprungen. Der Sensor behält seinen letzten bekannten Wert.
