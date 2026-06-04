# 3.0.0 - WebSocket-Echtzeitmodus, native Wallbox-Steuerung & Firmware 8.50

Version 3.0.0 bringt einen Echtzeit-Modus über WebSocket, steuert die Wallbox ohne separates Add-on und reduziert die Last auf der Enpal Box durch inkrementelles RenderBatch-Parsing.

---

## 🔌 Wichtig: Enpal-Firmware 8.50 für die neuen Funktionen

> Die neuen Echtzeit- und Wallbox-Funktionen setzen die Enpal-Firmware `Solar Rel. 8.50.1-773465 (27.05.2026)` voraus.
>
> - Der **WebSocket-Modus** (Echtzeit-Daten) und die **native Wallbox-Steuerung ohne Add-on** funktionieren nur mit Firmware **8.50**.
> - Das **inkrementelle RenderBatch-Parsing** basiert auf dem Datenformat von Firmware **8.50**.
> - Auf älteren Firmware-Ständen bleibt der **HTML-Polling-Modus (Legacy)** nutzbar, ohne die neuen Echtzeit- und Wallbox-Funktionen.
> - Enpal verteilt die Firmware automatisch. Eine manuelle Auswahl ist nicht möglich.

---

## 🎉 Was ist neu gegenüber 2.3.1?

### WebSocket-Verbindung (Echtzeit-Daten)

Bisher hat die Integration regelmäßig die Webseite der Enpal Box abgefragt und die angezeigten Daten ausgelesen (HTML-Scraping). Das funktioniert, ist aber langsam und kann bei Änderungen an der Webseite brechen.

Der neue WebSocket-Modus nutzt die native Schnittstelle der Enpal Box. Das ist dieselbe Technik, die auch die Weboberfläche intern verwendet. Die Daten werden direkt und in Echtzeit an Home Assistant übertragen.

- Sensor-Werte werden sofort aktualisiert statt nur alle 60 Sekunden.
- Die Integration hängt nicht mehr an der HTML-Struktur der Webseite.
- Eine dauerhafte Verbindung ersetzt die ständigen Seitenaufrufe.
- Die WebSocket-API liefert zusätzliche aggregierte Werte (z.B. Tagesverbrauch, Gesamthausleistung).

### Native Wallbox-Steuerung (ohne Add-on)

Bisher war zum Steuern der Wallbox ein separates Home Assistant Add-on nötig. Im WebSocket-Modus kommuniziert die Integration jetzt direkt mit der Wallbox-Seite der Enpal Box. Das separate Wallbox Add-on bzw. die Wallbox App wird im WebSocket-Modus nicht mehr benötigt.

- Keine zusätzliche Installation eines Add-ons.
- Direkter Befehlsweg ohne Umweg über ein Add-on.
- Die Wallbox-Steuerung aktivierst du direkt in den Integrationseinstellungen.

Unterstützte Wallbox-Funktionen: Laden starten und stoppen, Lademodus wechseln (Eco, Solar, Full, Smart), Wallbox-Status auslesen.

> **Wallbox App / Add-on im WebSocket-Modus deaktivieren.** Stoppe das alte Wallbox Add-on bzw. die Wallbox App. Sonst kommen sich die direkte Steuerung der Integration und das Add-on in die Quere und es entstehen doppelte Steuerbefehle. Nur im HTML-Polling-Modus (Legacy) wird das Add-on bzw. die App weiterhin gebraucht.

### Automatische Erkennung der Datenquelle

Bei der Einrichtung erkennt die Integration automatisch, ob die Enpal Box WebSocket unterstützt. Du musst dich nicht mit technischen Details befassen.

- **Auto-detect (empfohlen):** Prüft automatisch, ob WebSocket verfügbar ist.
- **WebSocket (Echtzeit):** Erzwingt die neue WebSocket-Verbindung.
- **HTML-Polling (Legacy):** Nutzt die bisherige Methode für ältere Enpal-Boxen.

### Inkrementelles RenderBatch-Parsing (weniger Last auf der Enpal Box)

Im WebSocket-Modus sendet die Box bei jeder Änderung (etwa alle 5 Sekunden) ein Änderungs-Paket (RenderBatch). Die Integration wertet jetzt dieses Paket direkt aus und aktualisiert nur die tatsächlich geänderten Sensoren, ohne erneuten Seitenabruf.

- Geringere CPU-Last der Enpal Box, weil der vollständige Seitenabruf bei jedem Update entfällt.
- Weniger Netzwerklast, weil Änderungen direkt aus dem WebSocket-Datenstrom gelesen werden.
- Echtzeit bleibt erhalten. Geänderte Werte erscheinen weiterhin sofort in Home Assistant.
- Als Sicherheitsnetz läuft im Hintergrund weiterhin ein vollständiger Abgleich im eingestellten Aktualisierungsintervall (Standard 60 s). Er hält alle Werte konsistent.

Einige wenige Sensoren tragen in mehreren Gerätegruppen denselben Namen (z.B. Phasen-Leistung oder -Spannung in Inverter und PowerSensor). Diese aktualisiert die Integration über den regelmäßigen Vollabgleich statt in Echtzeit. Die Werte bleiben korrekt, erscheinen aber erst im eingestellten Intervall.

### Dynamische Sensoren zur Laufzeit

Sensoren werden zur Laufzeit angelegt, sobald die Box neue Datenpunkte liefert. Verschwindet ein Sensor vorübergehend, behält die Entität ihren letzten Wert statt auf `unavailable` zu springen. Über `RestoreEntity` bleiben Tageswerte und Zustände über einen Neustart von Home Assistant erhalten.

### Zuverlässigere Wallbox-Status-Erkennung

Je nach Firmware liefert die Enpal Box den Wallbox-Status-Sensor unter unterschiedlichen Namen. Auf manchen Boxen (z.B. Enpal ArC GEN2) heißt der Rohsensor `Status.Connector.1` statt `Status.Wallbox.Connector.1`. Die automatische Erkennung berücksichtigt jetzt beide Namensvarianten.

Findet die Integration bei aktiver Wallbox-Steuerung keinen passenden Status-Sensor, legt sie eine Reparatur-Meldung in Home Assistant an (**Einstellungen → System → Reparaturen**). Über **Beheben** wählst du den richtigen Wallbox-Sensor direkt aus. Nach der Auswahl lädt die Integration neu und zeigt den Status an. Die Meldung verschwindet automatisch, sobald der Status-Sensor gefunden wird.

---

## ⚠️ Fehlende Sensoren seit Firmware 8.50

> Seit Firmware **8.50** stellt Enpal einige Sensoren nicht mehr bereit. Die Integration kann das nicht ändern. Fehlende Werte kommen daher, dass die Enpal Box sie nicht mehr liefert.
>
> Die dauerhaft nicht mehr verfügbaren Sensoren kannst du in Home Assistant gefahrlos löschen (über **Einstellungen → Geräte & Dienste → Entitäten** die jeweilige Entität auswählen und entfernen). Liefert Enpal einen Sensor später wieder, legt die Integration ihn automatisch neu an.

---

## 🔧 Installation und Upgrade

### Über HACS:
1. In HACS → **Enpal Solar** öffnen
2. Auf die **drei Punkte** (⋮) klicken → **Version auswählen**
3. Version **3.0.0** auswählen und installieren
4. Home Assistant **neu starten**

### Bestehende Installation upgraden:
1. Vor dem Upgrade ein **Home Assistant-Backup** anlegen.
2. Version **3.0.0** über HACS installieren (siehe oben).
3. Home Assistant **neu starten**.
4. Optional: **Einstellungen → Geräte & Dienste → Enpal Solar → Konfigurieren** öffnen und bei **Datenquelle** die gewünschte Option wählen (oder "Auto-detect" belassen).
5. Bestehende Einstellungen bleiben erhalten.

---

## ⚠️ Bekannte Einschränkungen

- **Firmware 8.50 nötig** für WebSocket-, Wallbox- und RenderBatch-Funktionen (siehe oben).
- **Wallbox App / Add-on im WebSocket-Modus deaktivieren.** Es wird nicht mehr gebraucht und kann sonst mit der direkten Steuerung kollidieren.
- **Mehrdeutige Sensoren** (gleicher Name in mehreren Gruppen) aktualisieren erst im Vollabgleich-Intervall statt in Echtzeit.
- **WebSocket-Verfügbarkeit:** Nicht alle Enpal-Boxen unterstützen WebSocket. Die Integration erkennt das automatisch und fällt im Zweifel auf HTML-Polling zurück.
- **Sensor-Unterschiede zwischen den Modi:** Im WebSocket-Modus stehen teilweise andere Sensoren zur Verfügung als im HTML-Modus. Siehe [Sensor-Vergleich](SENSOR_COMPARISON.md) für Details.
- **Nur 1. Generation Enpal Boxen** mit lokaler Weboberfläche werden unterstützt.

---

## ℹ️ Kompatibilität

- **Rückwärtskompatibel:** Bestehende Installationen werden automatisch migriert. Die Datenquelle wird beim Upgrade von 2.3.1 auf "HTML" gesetzt, damit alles wie gewohnt funktioniert. Die Option `use_wallbox_addon` wird automatisch in `use_wallbox` umbenannt.
- **Keine Breaking Changes:** Bestehende Sensoren und historische Daten bleiben unverändert. Beim Wechsel der Datenquelle (HTML → WebSocket) können sich einzelne Sensor-IDs ändern. Bestehende Historien bleiben erhalten, neue Sensoren starten ohne Historie.
- **Firmware:** Getestet mit Enpal Firmware Solar Rel. **8.50.1-773465 (27.05.2026)**.

---

## 🙏 Dank

Vielen Dank an alle Tester für das Feedback und die Geduld. Das WebSocket-Protokoll basiert auf dem Reverse-Engineering von @arigon.

Rückmeldungen bitte auf [GitHub Issues](https://github.com/derolli1976/enpal/issues) oder in den [GitHub Discussions](https://github.com/derolli1976/enpal/discussions).
