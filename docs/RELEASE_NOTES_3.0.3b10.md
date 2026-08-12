# 3.0.3b10 - Firmware 8.51 (Beta)

Enpal hat mit **Solar Rel. 8.51** die Seite `/deviceMessages` umgebaut. Auf Boxen mit dieser Firmware zeigen viele Sensoren seitdem Fehlertexte statt Messwerten an. Diese Beta behebt das.

Getestet wurde gegen zwei Seitenstände: `8.51.0-950631` und `8.51.0-955735`.

Gegenüber 3.0.3b9 behebt diese Beta den Grund, warum die Schalter-Klicks weiterhin fehlschlugen: Sie gingen an das falsche interne Objekt der Box.

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

## 🐛 Behoben gegenüber b7: Nur noch 4 Sensoren nach dem Start

b7 hat die neuen Seitenschalter direkt beim Verbindungsaufbau angeklickt. Das erste Datenpaket der Box trifft aber ein, während der Verbindungsaufbau noch läuft. Ein Klick in diesen halb gestarteten Circuit hat ihn zum Absturz gebracht.

Dazu kam ein zweiter, älterer Fehler: Stirbt der Circuit während des Verbindungsaufbaus, hat die Integration die Verbindung trotzdem als aufgebaut markiert. Der HTTP-Abruf lief weiter (daher die vier "Site Data"-Sensoren alle 60 Sekunden), aber es kamen nie wieder Datenpakete an, und es gab keinen neuen Verbindungsversuch.

Beides ist behoben:

- Ein Circuit-Abbruch während des Verbindungsaufbaus wird erkannt. Der Aufbau schlägt dann sauber fehl und wird beim nächsten Abruf wiederholt.
- Eine tote Verbindung (geschlossener Socket oder beendete Leseschleife) gilt nicht mehr als verbunden. Der nächste Abruf baut sie neu auf.

---

## 🐛 Behoben gegenüber b9: Klicks gingen an das falsche Objekt

b9 hat das erste Problem gelöst (veraltete Klick-Kennungen), aber die Klicks schlugen weiter fehl. Zwei Sniffer-Aufzeichnungen zeigen die zweite Ursache eindeutig:

Beim Verbindungsaufbau vergibt die Box Referenzen auf mehrere interne Objekte. Objekt 1 ist der Renderer, der die Klicks entgegennimmt. Die Objekte 2 bis 4 gehören zu den drei Diagrammen der Seite. Die Integration hat die Renderer-Referenz aus jeder passenden Nachricht übernommen und dabei mit den Diagramm-Referenzen überschrieben. Alle Klicks gingen dadurch an ein Diagramm-Objekt und liefen dort in eine Exception.

Das erklärt auch das wechselhafte Verhalten: Ob ein Klick funktionierte, hing davon ab, welche Nachricht zuletzt verarbeitet wurde.

Die Referenz wird jetzt nur noch aus der einen Nachricht übernommen, die den Renderer anmeldet (`attachWebRendererInterop`). Die Auswertung der Aufzeichnungen bestätigt: Die in b9 verwendeten Klick-Kennungen waren in 78 von 80 Fällen gültig, nur das Zielobjekt war falsch.

---

## 🐛 Behoben in b9: Klick-Kennungen veralten

Eine Aufzeichnung des kompletten Nachrichtenverkehrs (Danke an den Tester aus Issue #148) hat die Ursache gezeigt: Die Box verwirft die internen Klick-Kennungen aller Schalter bei jeder Aktualisierung der Seite und vergibt neue. Das passiert etwa alle 1,5 bis 5 Sekunden. b8 hat die Kennungen aus dem ersten Datenpaket gespeichert und Sekunden später damit geklickt. Zu diesem Zeitpunkt waren sie längst ungültig. Die Box hat jeden Klick mit einer Fehlermeldung abgelehnt.

Wichtig: Die Aufzeichnung zeigt auch, dass die abgelehnten Klicks harmlos sind. Die Verbindung lief dabei über Minuten stabil weiter.

b9 merkt sich statt der Kennung die Position jedes Schalters auf der Seite. Aus jedem Datenpaket werden die frischen Kennungen ausgelesen und über die Position den Schaltern zugeordnet. Geklickt wird immer mit der aktuellen Kennung. Wird ein Klick trotzdem abgelehnt, folgt ein neuer Versuch mit der nächsten frischen Kennung, maximal acht Mal pro Schalter. Ein angenommener Klick wird nicht wiederholt.

Die Zuordnung wurde offline gegen die komplette Aufzeichnung geprüft (204 Datenpakete, über 5 Minuten). Sie trifft in jedem Paket die gerade gültigen Kennungen.

---

## 🔋 Batterie-Ladestand kommt zurück

Der Ladestand `Energy.Battery.Charge.Level` fehlte auf 8.51 komplett. Die Gruppe "Battery" enthielt nur noch die maximale AC-Leistung und die Seriennummern.

Zwei Nutzer haben die Ursache eingegrenzt: Die Seite hat pro Gerätekarte neue Schalter "Show unsupported values" und "Show internal values". Der Ladestand liegt dahinter. Die Schalter sind ab Werk aus, und ausgeblendete Zeilen werden nicht übertragen. Sie gelten außerdem nur für die jeweilige Verbindung. Ein Aktivieren im Browser hilft der Integration also nicht, weil deren Verbindung ein eigener Blazor-Circuit ist.

Die Integration aktiviert die Schalter deshalb selbst:

- Die Schalter und ihre Position auf der Seite werden aus dem ersten Datenpaket der Box erkannt. Geklickt wird erst, wenn die Verbindung stabil steht (frühestens 5 Sekunden nach dem Circuit-Start), und immer mit der aktuellen Klick-Kennung aus dem letzten Datenpaket.
- Jeder Schalter wird über denselben Mechanismus angeklickt, mit dem auch die Wallbox-Buttons bedient werden. Pro Datenpaket wird ein Schalter gesetzt.
- Erfolg und Fehlschläge stehen im Protokoll (`Enabled page toggle 'showInternal_Battery'`).
- Als Sicherung aus b8: Bricht der Circuit kurz nach einem Klick ab, deaktiviert die Integration die Schalter-Aktivierung für den Rest der Laufzeit und verhält sich wie b6. Im Protokoll steht dann `Disabling page-toggle activation`.

Sobald die ausgeblendeten Zeilen übertragen werden, legt die Sensor-Erzeugung aus b6 die zugehörigen Entitäten automatisch an. Für `Energy.Battery.Charge.Level` bleibt die Entity-ID `sensor.battery_energy_battery_charge_level` erhalten.

---

## 🔧 Installation

1. In HACS → **Enpal Solar** öffnen
2. Auf die **drei Punkte** (⋮) klicken → **Version auswählen**
3. **Beta-Versionen einblenden** aktivieren
4. Version **3.0.3b10** auswählen und installieren
5. Home Assistant **neu starten**

Bestehende Einstellungen bleiben erhalten. Ein Neuaufsetzen der Integration ist nicht nötig.

---

## 🔌 Firmware-Hinweis

Der WebSocket-Modus setzt weiterhin **Solar Rel. 8.50** oder neuer voraus. Auf älteren Ständen läuft der HTML-Polling-Modus unverändert. Die Korrekturen dieser Version wirken in beiden Modi.
