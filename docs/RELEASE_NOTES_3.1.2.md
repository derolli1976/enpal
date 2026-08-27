# 3.1.2 - Fixes für Firmware 8.51.1 (Wallbox-Status und DC-Leistungssensor)

Bugfix-Release für zwei Probleme, die mit dem Firmware-Update auf **Solar Rel. 8.51.1** aufgetreten sind.

---

## 🐛 Behobene Fehler

### Wallbox-Status "Unknown" auf Firmware 8.51.1

Mit Firmware 8.51.1 blieb `sensor.wallbox_status` dauerhaft auf "Unknown", obwohl das Auto lud. Die Firmware hat zwei Dinge geändert: Die Seite `/wallbox` wird nicht mehr vorgerendert und die Statuskarte heißt jetzt "Connector Charging" statt "Status Charging". Die Integration liest beide Formate jetzt korrekt und hält die WebSocket-Verbindung zur Wallbox-Seite offen, damit Statusänderungen weiter ankommen. Der Lademodus war nicht betroffen.

### Warnungs-Flut "No suitable DC power sensor found" (Issue #177)

Seit Firmware 8.51 liefert der erste Datenabruf nur die Karte "Site Data". Die Inverter-Sensoren kommen wenige Sekunden später über den WebSocket. Die Auswahl des DC-Leistungssensors für `sensor.inverter_energy_produced_total_dc` lief aber nur einmal beim Start. Sie fand deshalb nichts, fiel fest auf den Huawei-Sensor zurück und schrieb danach bei jedem Update eine Warnung ins Log. Auf FoxESS-Systemen kamen so zehntausende Einträge zusammen.

Die Sensor-Auswahl läuft jetzt bei jedem Update, bis ein passender Sensor gefunden ist. Nachträglich eintreffende Sensoren werden erkannt, auch herstellerspezifische wie bei SMA oder FoxESS. Die Warnung erscheint höchstens einmal.

### Sensor "Inverter System State" dauerhaft "nicht verfügbar" (Issue #178)

Seit Firmware 8.51 kommt der System-Status des Inverters nur noch über den WebSocket, als langer HTML-Block. Die Integration hat daraus zwar die aufgeteilten Sensoren erzeugt (Decimal, Flags, einzelne Bits), den Basis-Sensor `sensor.inverter_system_state` aber nicht mehr beliefert. Er stand deshalb dauerhaft auf "nicht verfügbar".

Der Basis-Sensor erhält jetzt wieder einen Wert: den Statustext ohne HTML-Formatierung, gekürzt auf eine für Home Assistant gültige Länge. Das entspricht dem Verhalten aus dem HTML-Modus vor Firmware 8.51. Die Entity-ID bleibt unverändert.

## 🔄 Kompatibilität

- Keine Änderungen an Entity-IDs, Sensoren oder Optionen
- Die Prioritätsreihenfolge der DC-Sensor-Auswahl bleibt unverändert: Huawei, herstellerspezifisch, generisch, berechnet

## ❤️ Unterstützung

Wenn dir die Integration hilft und du die Weiterentwicklung unterstützen möchtest, freue ich mich über eine Spende über die **Sponsoring-Sektion** dieses Repositories (Button "Sponsor" oben auf der [Projektseite](https://github.com/derolli1976/enpal)) oder über [Buy Me a Coffee](https://buymeacoffee.com/derolli1976). Danke!
