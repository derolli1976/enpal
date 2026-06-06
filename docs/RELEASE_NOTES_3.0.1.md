# 3.0.1 - Bugfix für eingefrorene und fehlende Sensoren im WebSocket-Modus

3.0.1 ist ein Bugfix-Release. Es behebt ein Problem, bei dem einzelne Sensoren im WebSocket-Modus nach einem Neustart von Home Assistant einfrieren oder auf `unavailable` stehen bleiben konnten. Betroffen war vor allem `Energy.Consumption.Total.Lifetime`. Danke an alle, die das gemeldet und beim Eingrenzen geholfen haben.

Es sind keine Einrichtungsschritte nötig. Bestehende Einstellungen bleiben erhalten.

---

## 🐛 Behobene Fehler

### Sensor bleibt nach Neustart auf `unavailable`

Fehlte ein Sensor beim ersten Datenabruf direkt nach dem Start, wurde er nicht mehr nachträglich angelegt. Ursache war der Echtzeit-Datenstrom: Jeder WebSocket-Push hat den Timer für den regelmäßigen Vollabgleich zurückgesetzt. Dadurch lief der Vollabgleich nie, und ein anfangs fehlender Sensor blieb dauerhaft leer.

Der Push aktualisiert die Daten jetzt direkt, ohne den Timer für den Vollabgleich zurückzusetzen. Der Vollabgleich läuft damit wieder zuverlässig im eingestellten Intervall (Standard 60 s) und legt fehlende Sensoren nach, sobald die Box sie liefert.

### Sensor zeigt einen eingefrorenen Wert

In seltenen Fällen konnte ein Änderungs-Paket (RenderBatch) nur den Zeitstempel eines Sensors enthalten. Dieser Zeitstempel wurde dann als Wert in einen numerischen Sensor geschrieben. Der Wert war nicht mehr als Zahl interpretierbar, der Sensor fror ein oder wurde `unavailable`, während sich nur noch `enpal_last_update` bewegte.

Numerische Sensoren übernehmen jetzt nur noch gültige Zahlenwerte aus dem Echtzeit-Datenstrom. Ein reiner Zeitstempel überschreibt den Messwert nicht mehr. Der vorhandene Wert bleibt erhalten, bis ein gültiger neuer Wert kommt.

### Weniger Warnungen beim Start

Beim Start wurden die Wallbox-Plattformen eingerichtet, bevor die zugehörigen Status-Sensoren existierten. Das hat kurzzeitig Warnungen zu `sensor.wallbox_status` und `sensor.wallbox_lademodus` erzeugt, obwohl die Werte danach korrekt erschienen. Diese erwartbare Start-Meldung läuft jetzt auf Log-Level `debug` statt `warning`.

---

## 🔧 Installation und Upgrade

### Über HACS:
1. In HACS → **Enpal Solar** öffnen
2. Auf die **drei Punkte** (⋮) klicken → **Version auswählen**
3. Version **3.0.1** auswählen und installieren
4. Home Assistant **neu starten**

### Bestehende Installation upgraden:
1. Vor dem Upgrade ein **Home Assistant-Backup** anlegen.
2. Version **3.0.1** über HACS installieren (siehe oben).
3. Home Assistant **neu starten**.
4. Bestehende Einstellungen bleiben erhalten.

---

## 🔌 Firmware-Hinweis

Die WebSocket-Funktionen setzen weiterhin die Enpal-Firmware **Solar Rel. 8.50** voraus. Auf älteren Firmware-Ständen läuft der HTML-Polling-Modus (Legacy) unverändert. Details zu den Funktionen aus dem letzten großen Release stehen in den [Release Notes 3.0.0](RELEASE_NOTES_3.0.0.md).
