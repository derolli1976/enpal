# 3.0.3b5 - Firmware 8.51 (Beta)

Enpal hat mit **Solar Rel. 8.51** die Seite `/deviceMessages` umgebaut. Auf Boxen mit dieser Firmware zeigen viele Sensoren seitdem Fehlertexte statt Messwerten an. Diese Beta behebt das.

Getestet wurde gegen zwei Seitenstände: `8.51.0-950631` und `8.51.0-955735`.

Gegenüber 3.0.3b4 wird der Verbindungsabbruch an einer weiteren Stelle angegangen. Auf einer Box stehen weiterhin fast alle Sensoren auf "nicht verfügbar". Die Ursache ist bekannt und weiter unten beschrieben.

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

Neu in b5: von den ersten drei großen Datenpaketen einer Verbindung wird der Inhalt der Zeichenkettentabelle mitgeschrieben. Damit lässt sich nachvollziehen, was die Box tatsächlich überträgt, und daraus die künftige Auswertung bauen.

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

b4 hat die Popover-Abfrage mit einer Zahl beantwortet. Das hat den Abbruch seltener gemacht, aber nicht beseitigt. b5 beantwortet zusätzlich die drei Diagramm-Aufrufe mit den Abmessungen, die sie erwarten.

---

## 🚧 Bekanntes Problem auf 8.51

Auf mindestens einer Box stehen trotz dieser Korrekturen fast alle Sensoren auf "nicht verfügbar". Der Grund liegt tiefer als die Auswertung.

Ruft man `/deviceMessages` direkt über HTTP ab, enthält die Antwort nur noch die Karte "Site Data" mit Werten. Alle Gerätekarten sind leer und tragen den Hinweis `No messages available for this device.` Die Zeilen entstehen erst, wenn die Box ihre Weboberfläche über eine offene Verbindung nachlädt. Im Browser sieht die Seite deshalb vollständig aus, beim Abruf durch die Integration nicht.

Damit liefert der HTML-Modus auf diesen Boxen nur noch die vier Werte aus "Site Data". Der WebSocket-Modus könnte die Lücke schließen, aber die Box beendet die Verbindung kurz nach dem Aufbau wieder, bevor Daten ankommen.

Ob eine Box betroffen ist, zeigt das Debug-Protokoll:

```
[Enpal] Parsed cards: Site Data=4, Battery=0, IoTEdgeDevice=0, PowerSensor=0, Wallbox=0, Inverter=0
```

Stehen dort überall Nullen außer bei "Site Data", greift das Problem. Der Fix dafür ist in Arbeit. Die Daten müssen künftig aus der laufenden Verbindung gelesen werden statt aus dem HTTP-Abruf. Das erste Datenpaket nach dem Verbindungsaufbau enthält die Werte noch nicht, es entspricht dem leeren HTTP-Abruf. Sie kommen erst später, wenn die Box die Gerätedaten nachlädt. Dafür muss die Verbindung stehen bleiben. Diese Beta arbeitet daran und protokolliert, was die Box sendet. Die Sensoren füllen sich damit noch nicht.

---

## 🔍 Bekannte Einschränkung

Der Batterie-Ladestand `Energy.Battery.Charge.Level` fehlt auf beiden getesteten 8.51-Seiten komplett. Die Gruppe "Battery" enthält nur noch die maximale AC-Leistung und die Seriennummern.

Die Seite hat neue Schalter "Show unsupported values" und "Show internal values". Sie sind ab Werk nicht gesetzt, und ausgeblendete Zeilen stehen nicht im Quelltext. Ob der Ladestand dahinter liegt oder wirklich entfallen ist, lässt sich erst klären, wenn die Datenanbindung auf 8.51 wieder läuft.

---

## 🔧 Installation

1. In HACS → **Enpal Solar** öffnen
2. Auf die **drei Punkte** (⋮) klicken → **Version auswählen**
3. **Beta-Versionen einblenden** aktivieren
4. Version **3.0.3b5** auswählen und installieren
5. Home Assistant **neu starten**

Bestehende Einstellungen bleiben erhalten. Ein Neuaufsetzen der Integration ist nicht nötig.

---

## 🔌 Firmware-Hinweis

Der WebSocket-Modus setzt weiterhin **Solar Rel. 8.50** oder neuer voraus. Auf älteren Ständen läuft der HTML-Polling-Modus unverändert. Die Korrekturen dieser Version wirken in beiden Modi.
