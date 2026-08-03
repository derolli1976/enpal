# 3.0.3b6 - Firmware 8.51 (Beta)

Enpal hat mit **Solar Rel. 8.51** die Seite `/deviceMessages` umgebaut. Auf Boxen mit dieser Firmware zeigen viele Sensoren seitdem Fehlertexte statt Messwerten an. Diese Beta behebt das.

Getestet wurde gegen zwei Seitenstände: `8.51.0-950631` und `8.51.0-955735`.

Gegenüber 3.0.3b5 liest der WebSocket-Modus die Sensordaten jetzt direkt aus den Datenpaketen der Box. Damit füllen sich die Sensoren auch auf Boxen, deren HTTP-Abruf leer bleibt.

---

## ⚠️ Beta-Version

> Diese Version ist zum Testen gedacht.
>
> - 💾 Vor der Installation ein Home Assistant-Backup anlegen.
> - 🔄 Bei Problemen kannst du über HACS jederzeit auf 3.0.2 zurückwechseln.
> - 🐛 Auffälligkeiten bitte in [Issue #148](https://github.com/derolli1976/enpal/issues/148) melden.

---

## 🐛 Behobene Fehler

### Sensoren zeigen Fehlertexte statt Werte

Firmware 8.51 hat den Tabellen eine Spalte "Notes" hinzugefügt. Zeilen ohne gültigen Messwert enthalten keine Wert- und Zeitstempelspalte mehr. Stattdessen steht dort eine Notiz über die restliche Zeilenbreite, zum Beispiel `missing: The value has been cleared.`

Der Parser hat diese Notiz als Messwert gelesen. Betroffene Sensoren standen danach auf Texten wie `missing: Device provided value ProcessImageValueKey { KeyString = Power.Reactive } has not been set`. Bei einem Nutzer waren 65 von 135 Sensoren betroffen.

Zeilen ohne Messwert werden jetzt übersprungen. Der Sensor behält seinen letzten bekannten Wert, bis die Box wieder einen Wert liefert.

### Neue Entitäten nach dem Firmware-Update

Firmware 8.51 hat neun Datenpunkte in der Gruppe "Inverter" um das Suffix `.Inverter` erweitert. Home Assistant hätte daraus neue Entitäten mit neuen IDs erzeugt. Automatisierungen und Verlaufsdaten wären ins Leere gelaufen.

Diese Schlüssel werden jetzt auf ihre bisherigen Namen zurückgeführt:

| Firmware 8.51 | Entity-ID bleibt |
| --- | --- |
| `Power.AC.Phase.A.Inverter` | `sensor.inverter_power_ac_phase_a` |
| `Power.AC.Phase.B.Inverter` | `sensor.inverter_power_ac_phase_b` |
| `Power.AC.Phase.C.Inverter` | `sensor.inverter_power_ac_phase_c` |
| `Power.Battery.Charge.Discharge.Inverter` | `sensor.inverter_power_battery_charge_discharge` |
| `Power.Battery.Charge.Max.Inverter` | `sensor.inverter_power_battery_charge_max` |
| `Power.Battery.Discharge.Max.Inverter` | `sensor.inverter_power_battery_discharge_max` |
| `Energy.Battery.Charge.Day.Inverter` | `sensor.inverter_energy_battery_charge_day` |
| `Energy.Battery.Discharge.Day.Inverter` | `sensor.inverter_energy_battery_discharge_day` |
| `Mode.Forcible.Charge.Discharge.Inverter` | `sensor.inverter_mode_forcible_charge_discharge` |

Die Zuordnung gilt für beide Datenquellen, also auch für die WebSocket-Updates.

---

## 🔎 Neue Diagnose-Ausgabe

Bei aktivierter Debug-Protokollierung schreibt die Integration jetzt pro Abruf mit, welche Karten der Seite gelesen wurden und wie viele Sensoren jede davon geliefert hat. Karten, deren Gruppe in den Einstellungen nicht ausgewählt ist, werden getrennt aufgeführt. Zeilen ohne Messwert werden pro Gruppe gezählt.

Wenn gar kein Sensor gelesen werden konnte, erscheint eine Warnung mit der Größe der Seite und den gefundenen Karten. Damit lässt sich unterscheiden, ob die Box nichts liefert oder ob die Auswertung scheitert.

Neu in dieser Beta: die WebSocket-Verbindung protokolliert ihren kompletten Nachrichtenverkehr. Jede eingehende Anfrage der Box, jeder JavaScript-Aufruf und jede Antwort auf unsere Aufrufe werden mitgeschrieben. Beendet die Box die Verbindung, steht im Protokoll zusätzlich, wie lange die Verbindung bestand und welche Nachrichten zuletzt eingegangen sind. Fehlermeldungen der Box werden im Klartext ausgegeben statt verworfen. Zu jedem empfangenen Datenpaket steht die Größe, die Anzahl enthaltener Zeichenketten und die Anzahl erkannter Sensorzeilen im Protokoll.

Neu in b5: von den ersten drei großen Datenpaketen einer Verbindung wird der Inhalt der Zeichenkettentabelle mitgeschrieben. Damit lässt sich nachvollziehen, was die Box tatsächlich überträgt. Genau diese Ausgabe hat die Grundlage für die neue Auswertung in b6 geliefert.

---

## 🔌 Verbindung bricht direkt nach dem Aufbau ab

Firmware 8.51 hat der Seite Diagramme und eine Popover-Komponente hinzugefügt. Beim Verbindungsaufbau fragt die Box dafür mehrere JavaScript-Funktionen ab und erwartet Antworten. Die Integration hat auf alle diese Anfragen mit einem leeren Wert geantwortet. Auf der Box läuft das in einen Fehler, und sie beendet die Verbindung nach einer halben Sekunde wieder.

Im Protokoll sah das so aus:

```
JS call Radzen.createChart([...])
JS call mudpopoverHelper.countProviders(None)
Circuit error reported by the box: There was an unhandled exception on the current circuit
Server sent Close: None (0.4s after StartCircuit)
```

b4 hat die Popover-Abfrage mit einer Zahl beantwortet. Das hat den Abbruch seltener gemacht, aber nicht beseitigt. b5 beantwortet zusätzlich die drei Diagramm-Aufrufe mit den Abmessungen, die sie erwarten. Ein Testlog aus b5 zeigt die Verbindung über mehr als 20 Minuten stabil, ohne einen einzigen Circuit-Fehler.

---

## 📡 Sensordaten kommen jetzt aus der WebSocket-Verbindung

Auf Firmware 8.51 enthält der HTTP-Abruf von `/deviceMessages` nur noch die Karte "Site Data". Alle Gerätekarten sind leer und tragen den Hinweis `No messages available for this device.` Die Zeilen entstehen erst in der laufenden Blazor-Verbindung. Im Browser sieht die Seite deshalb vollständig aus, beim Abruf durch die Integration nicht.

Die Logs aus b5 haben gezeigt: Sobald die Verbindung steht, schickt die Box etwa alle fünf Sekunden ein Datenpaket mit den geänderten Zeilen. Schlüssel, Wert, Einheit und Zeitstempel sind enthalten. Nur die Gruppe fehlt.

Diese Beta legt daraus Sensoren an:

- Taucht in einem Datenpaket ein Schlüssel auf, den die Integration noch nicht kennt, wird der Sensor direkt angelegt.
- Die Gruppe wird über eine feste Zuordnungstabelle bestimmt, damit die Entity-IDs identisch zu Firmware 8.50 bleiben. Verlauf und Automatisierungen laufen weiter.
- Schlüssel ohne bekannte Gruppe werden übersprungen. Eine falsche ID wäre schlimmer als ein fehlender Sensor.
- Die so angelegten Sensoren überleben den periodischen HTTP-Abruf, der auf 8.51 weiterhin fast leer zurückkommt.

Die Auswertung der Datenpakete versteht jetzt auch das neue Zeilenformat von 8.51 mit der Spalte "Notes". Zeilen ohne Messwert werden übersprungen, der Sensor behält seinen letzten Wert. Wh-Werte werden wie bisher in kWh umgerechnet.

Zwei Einschränkungen bleiben:

- Es erscheinen nur Sensoren, deren Werte sich ändern. Statische Werte wie Seriennummern tauchen erst auf, wenn die Box sie einmal aktualisiert.
- Der Inverter-Systemstatus wird auf 8.51 als langer HTML-Text übertragen und im WebSocket-Modus noch nicht in Einzelsensoren zerlegt.

Der HTML-Modus liefert auf betroffenen Boxen weiterhin nur die Werte aus "Site Data". Wenn deine Box betroffen ist, stelle die Integration in den Einstellungen auf den WebSocket-Modus um.

---

## 🔍 Bekannte Einschränkung

Der Batterie-Ladestand `Energy.Battery.Charge.Level` fehlt auf beiden getesteten 8.51-Seiten komplett. Die Gruppe "Battery" enthält nur noch die maximale AC-Leistung und die Seriennummern.

Die Seite hat neue Schalter "Show unsupported values" und "Show internal values". Sie sind ab Werk nicht gesetzt, und ausgeblendete Zeilen stehen nicht im Quelltext. Ob der Ladestand dahinter liegt oder wirklich entfallen ist, ist weiter offen. Taucht er in den Datenpaketen der Box auf, legt diese Beta den Sensor automatisch wieder an.

---

## 🔧 Installation

1. In HACS → **Enpal Solar** öffnen
2. Auf die **drei Punkte** (⋮) klicken → **Version auswählen**
3. **Beta-Versionen einblenden** aktivieren
4. Version **3.0.3b6** auswählen und installieren
5. Home Assistant **neu starten**

Bestehende Einstellungen bleiben erhalten. Ein Neuaufsetzen der Integration ist nicht nötig.

---

## 🔌 Firmware-Hinweis

Der WebSocket-Modus setzt weiterhin **Solar Rel. 8.50** oder neuer voraus. Auf älteren Ständen läuft der HTML-Polling-Modus unverändert. Die Korrekturen dieser Version wirken in beiden Modi.
