# 3.0.2 - Geringere CPU-Last und korrekter Wallbox-Statussensor

3.0.2 ist ein Bugfix-Release. Es senkt die CPU-Last der Integration und behebt einen Fehler, bei dem ein Wallbox-Statussensor fälschlich als Spannungssensor behandelt wurde. Danke an alle, die das gemeldet und beim Eingrenzen geholfen haben.

Es sind keine Einrichtungsschritte nötig. Bestehende Einstellungen bleiben erhalten.

---

## 🐛 Behobene Fehler

### Höhere CPU-Last seit 3.0.0

Bei jedem Datenabgleich hat jede Entität die komplette Sensorliste durchsucht und dabei für jeden Eintrag die ID neu berechnet. Die ID-Berechnung lief so sehr oft pro Sekunde, vor allem im WebSocket-Modus mit vielen Sensoren. Das hat unnötig CPU-Last erzeugt.

Die ID-Berechnung wird jetzt zwischengespeichert. Wiederholte Aufrufe für denselben Namen kosten kaum noch Rechenzeit. Die Sensorwerte ändern sich dadurch nicht.

### Wallbox-Statussensor als Spannungssensor erkannt

Der Statussensor `Status.Connector.1` liefert Textwerte wie `SuspendedEV`, `Charging` oder `Unknown`. Die Einheitenerkennung hat das Schluss-`V` von `SuspendedEV` als Volt gelesen und den Sensor als Spannung mit Einheit `V` eingestuft. Home Assistant hat den Textwert dann abgelehnt und bei jedem Update einen Fehler geworfen.

Eine Einheit wird jetzt nur noch erkannt, wenn der Teil davor eine Zahl ist. Textwerte wie `SuspendedEV` bleiben einfache Textsensoren. Echte Messwerte wie `230 V` oder `1234 kWh` werden weiterhin korrekt eingeordnet.

---

## 🔧 Installation und Upgrade

### Über HACS:
1. In HACS → **Enpal Solar** öffnen
2. Auf die **drei Punkte** (⋮) klicken → **Version auswählen**
3. Version **3.0.2** auswählen und installieren
4. Home Assistant **neu starten**

### Bestehende Installation upgraden:
1. Vor dem Upgrade ein **Home Assistant-Backup** anlegen.
2. Version **3.0.2** über HACS installieren (siehe oben).
3. Home Assistant **neu starten**.
4. Bestehende Einstellungen bleiben erhalten.

---

## 🔌 Firmware-Hinweis

Die WebSocket-Funktionen setzen weiterhin die Enpal-Firmware **Solar Rel. 8.50** voraus. Auf älteren Firmware-Ständen läuft der HTML-Polling-Modus (Legacy) unverändert. Details zu den Funktionen aus dem letzten großen Release stehen in den [Release Notes 3.0.0](RELEASE_NOTES_3.0.0.md).
