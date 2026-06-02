# 2.9.9b3 - Inkrementelles RenderBatch-Parsing & Firmware 8.50 (Beta)

---

## ⚠️ BETA-VERSION — WICHTIGE HINWEISE

> **Dies ist eine Beta-Version und nicht für den produktiven Einsatz gedacht.**
>
> - 🧪 **Nur zum Testen.** Diese Version kann noch Fehler enthalten.
> - 💾 **Backup erstellen.** Lege vor der Installation ein Home Assistant-Backup an.
> - 🔄 **Downgrade möglich.** Bei Problemen kannst du über HACS jederzeit auf die stabile Version 2.3.0 zurückwechseln (drei Punkte → Version auswählen).
> - 🐛 **Fehler melden.** Bitte melde Fehler und Auffälligkeiten auf [GitHub Issues](https://github.com/derolli1976/enpal/issues).

---

## 🔌 Wichtig: Enpal-Firmware 8.50 erforderlich

> **Die neuen Echtzeit- und Wallbox-Funktionen setzen die Enpal-Firmware
> `Solar Rel. 8.50.1-773465 (27.05.2026)` voraus.**
>
> - Der **WebSocket-Modus** (Echtzeit-Daten) und die **native Wallbox-Steuerung ohne Add-on** funktionieren nur mit Firmware **8.50**.
> - Das neue **inkrementelle RenderBatch-Parsing** basiert auf dem Datenformat von Firmware **8.50**.
> - Auf älteren Firmware-Ständen bleibt der **HTML-Polling-Modus (Legacy)** nutzbar, ohne die neuen Echtzeit- und Wallbox-Funktionen.
> - Enpal verteilt die Firmware automatisch. Eine manuelle Auswahl ist nicht möglich.

---

## 🅿️ Wichtig: Wallbox App / Add-on im WebSocket-Modus deaktivieren

> Im **WebSocket-Modus** steuert die Integration die Wallbox direkt. Das früher benötigte
> separate Wallbox Add-on bzw. die Wallbox App wird nicht mehr gebraucht.
>
> - **Stoppe das alte Wallbox Add-on bzw. die Wallbox App.** Sonst kommen sich die direkte Steuerung der Integration und das Add-on in die Quere (doppelte Steuerbefehle).
> - Die Wallbox-Steuerung aktivierst du stattdessen direkt in den **Integrationseinstellungen**.
> - Nur im **HTML-Polling-Modus (Legacy)** wird das Add-on bzw. die App weiterhin gebraucht.

---

## ⚠️ Fehlende Sensoren seit Firmware 8.50

> Seit Firmware **8.50** stellt Enpal einige Sensoren nicht mehr bereit. Die Integration kann das
> nicht ändern. Fehlende Werte kommen daher, dass die Enpal Box sie nicht mehr liefert.
>
> Die dauerhaft nicht mehr verfügbaren Sensoren kannst du in Home Assistant gefahrlos löschen
> (über **Einstellungen → Geräte & Dienste → Entitäten** die jeweilige Entität auswählen und
> entfernen). Liefert Enpal einen Sensor später wieder, legt die Integration ihn automatisch neu an.

---

## 🎉 Was ist neu in 2.9.9b3?

### Inkrementelles RenderBatch-Parsing (weniger Last auf der Enpal Box)

**Das Problem:** Bisher hat die Integration im WebSocket-Modus bei jeder Änderungsmeldung der
Enpal Box (etwa alle 5 Sekunden) die komplette Geräteseite (`/deviceMessages`) neu abgerufen und
ausgewertet. Das erzeugt unnötige Last auf dem Prozessor der Enpal Box.

**Die Lösung:** Die Integration wertet jetzt die von der Box gesendeten Änderungs-Pakete
(RenderBatch) direkt aus und aktualisiert nur die tatsächlich geänderten Sensoren, ohne erneuten
Seitenabruf.

**Was sich dadurch ändert:**
- 📉 Geringere CPU-Last der Enpal Box, weil der vollständige Seitenabruf bei jedem Update entfällt.
- 🌐 Weniger Netzwerklast, weil Änderungen direkt aus dem WebSocket-Datenstrom gelesen werden.
- ⚡ Echtzeit bleibt erhalten. Geänderte Werte erscheinen weiterhin sofort in Home Assistant.
- 🛡️ Als Sicherheitsnetz läuft im Hintergrund weiterhin ein vollständiger Abgleich (im
  eingestellten Aktualisierungsintervall, Standard 60 s). Er hält alle Werte konsistent.

**Technischer Hinweis:** Einige wenige Sensoren tragen in mehreren Gerätegruppen denselben Namen
(z.B. Phasen-Leistung oder -Spannung in Inverter und PowerSensor). Diese aktualisiert die
Integration bewusst über den regelmäßigen Vollabgleich statt in Echtzeit. Die Werte bleiben
korrekt, erscheinen aber erst im eingestellten Intervall.

---

## 🔧 Installation der Beta

### Über HACS:
1. In HACS → **Enpal Solar** öffnen
2. Auf die **drei Punkte** (⋮) klicken → **Version auswählen**
3. Version **2.9.9b3** auswählen und installieren
4. Home Assistant **neu starten**

### Bestehende Beta-Installation upgraden:
1. Version **2.9.9b3** über HACS installieren (siehe oben)
2. Home Assistant **neu starten**
3. Es sind keine Konfigurationsänderungen nötig. Bestehende Einstellungen bleiben erhalten.

---

## ⚠️ Bekannte Einschränkungen (Beta)

- **Firmware 8.50 nötig** für WebSocket-, Wallbox- und RenderBatch-Funktionen (siehe oben).
- **Wallbox App / Add-on im WebSocket-Modus deaktivieren.** Es wird nicht mehr gebraucht und kann sonst mit der direkten Steuerung kollidieren (siehe oben).
- **Mehrdeutige Sensoren** (gleicher Name in mehreren Gruppen) aktualisieren erst im Vollabgleich-Intervall statt in Echtzeit.
- **WebSocket-Verfügbarkeit:** Nicht alle Enpal-Boxen unterstützen WebSocket. Die Integration erkennt das automatisch und fällt im Zweifel auf HTML-Polling zurück.
- **Verbindungsstabilität:** Die WebSocket-Verbindung wird bei Abbruch automatisch neu aufgebaut. In seltenen Fällen kann es zu kurzen Aussetzern kommen.

---

## 📋 Zurück zur stabilen Version

Falls Probleme auftreten:

1. In HACS → **Enpal Solar** öffnen
2. Auf die **drei Punkte** (⋮) klicken → **Version auswählen**
3. Version **2.3.0** (stabile Version) auswählen und installieren
4. Home Assistant **neu starten**

Alle bisherigen Sensoren und Einstellungen bleiben erhalten.

---

## ℹ️ Kompatibilität

- **Rückwärtskompatibel**: Bestehende Installationen werden automatisch migriert.
- **Keine Breaking Changes**: Bestehende Sensoren und historische Daten bleiben unverändert.
- **Firmware**: Getestet mit Enpal Firmware Solar Rel. **8.50.1-773465 (27.05.2026)**.

---

## 🙏 Feedback erwünscht

Diese Beta lebt von eurem Feedback. Besonders interessiert mich:

- 📉 Fällt die **CPU-Last der Enpal Box** nach dem Update spürbar geringer aus?
- ✅ Was funktioniert gut? ❌ Was funktioniert nicht?

Rückmeldungen bitte auf [GitHub Issues](https://github.com/derolli1976/enpal/issues) oder in den
[GitHub Discussions](https://github.com/derolli1976/enpal/discussions).
