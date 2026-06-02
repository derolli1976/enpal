# 2.9.9b3 - Inkrementelles RenderBatch-Parsing & Firmware 8.50 (Beta)

---

## ⚠️ BETA-VERSION — WICHTIGE HINWEISE

> **Dies ist eine Beta-Version und NICHT für den produktiven Einsatz gedacht!**
>
> - 🧪 **Nur zum Testen** — diese Version kann noch Fehler enthalten.
> - 💾 **Backup erstellen!** — Vor der Installation unbedingt ein Home Assistant-Backup anlegen.
> - 🔄 **Downgrade möglich** — Bei Problemen kann jederzeit auf die stabile Version 2.3.0 zurückgewechselt werden (über HACS → Version auswählen).
> - 🐛 **Fehler melden** — Bitte Fehler und Auffälligkeiten auf [GitHub Issues](https://github.com/derolli1976/enpal/issues) melden.

---

## 🔌 Wichtig: Enpal-Firmware 8.50 erforderlich

> **Die neuen Echtzeit- und Wallbox-Funktionen dieser Version setzen die Enpal-Firmware
> `Solar Rel. 8.50.1-773465 (27.05.2026)` voraus.**
>
> - Der **WebSocket-Modus** (Echtzeit-Daten) und die **native Wallbox-Steuerung ohne Add-on**
>   funktionieren nur mit Firmware **8.50**.
> - Das in dieser Version neue **inkrementelle RenderBatch-Parsing** basiert auf dem
>   Datenformat von Firmware **8.50**.
> - Auf älteren Firmware-Ständen bleibt der **HTML-Polling-Modus (Legacy)** nutzbar — jedoch
>   **ohne** die neuen Echtzeit- und Wallbox-Funktionen.
> - Die Firmware wird von Enpal automatisch verteilt; eine manuelle Auswahl ist nicht möglich.

---

## 🅿️ Wichtig: Wallbox App / Add-on im WebSocket-Modus deaktivieren

> Im **WebSocket-Modus** steuert die Integration die Wallbox **direkt** — das früher benötigte
> separate **Wallbox Add-on bzw. die Wallbox App wird nicht mehr benötigt**.
>
> - **Bitte das alte Wallbox Add-on / die Wallbox App in diesem Fall unbedingt
>   deaktivieren (stoppen)!** Andernfalls können sich die direkte Steuerung der Integration und
>   das Add-on gegenseitig in die Quere kommen (doppelte/konkurrierende Steuerbefehle).
> - Die Wallbox-Steuerung wird stattdessen direkt in den **Integrationseinstellungen** aktiviert.
> - Nur im **HTML-Polling-Modus (Legacy)** wird das Add-on / die App weiterhin benötigt.

---

## 🎉 Was ist neu in 2.9.9b3?

### Inkrementelles RenderBatch-Parsing (deutlich weniger Last auf der Enpal Box)

**Das Problem:** Bisher hat die Integration im WebSocket-Modus bei **jeder** Änderungsmeldung
der Enpal Box (etwa alle 5 Sekunden) die komplette Geräteseite (`/deviceMessages`) neu
abgerufen und ausgewertet. Das erzeugt unnötige Last auf dem Prozessor der Enpal Box.

**Die Lösung:** Die Integration wertet jetzt die von der Box gesendeten
**Änderungs-Pakete (RenderBatch)** direkt aus und aktualisiert **nur die tatsächlich
geänderten Sensoren** — ganz ohne erneuten Seitenabruf.

**Vorteile auf einen Blick:**
- 📉 **Geringere CPU-Last der Enpal Box** — kein vollständiger Seitenabruf mehr bei jedem Update
- 🌐 **Weniger Netzwerklast** — Änderungen werden direkt aus dem WebSocket-Datenstrom gelesen
- ⚡ **Echtzeit bleibt erhalten** — geänderte Werte erscheinen weiterhin sofort in Home Assistant
- 🛡️ **Sicherheitsnetz** — ein vollständiger Abgleich erfolgt weiterhin regelmäßig im
  Hintergrund (im eingestellten Aktualisierungsintervall, Standard 60 s), um alle Werte
  zuverlässig konsistent zu halten

**Technischer Hinweis:** Einige wenige Sensoren, deren Name in mehreren Gerätegruppen
identisch vorkommt (z.B. Phasen-Leistung/-Spannung in Inverter *und* PowerSensor), werden
bewusst weiterhin über den regelmäßigen Vollabgleich aktualisiert. Sie werden dadurch im
eingestellten Intervall (statt in Echtzeit) aktualisiert — die Werte bleiben korrekt.

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
3. Es sind **keine** Konfigurationsänderungen nötig — bestehende Einstellungen bleiben erhalten.

---

## ⚠️ Bekannte Einschränkungen (Beta)

- **Firmware 8.50 nötig** für WebSocket-, Wallbox- und RenderBatch-Funktionen (siehe oben).
- **Wallbox App / Add-on im WebSocket-Modus deaktivieren** — wird nicht mehr benötigt und kann
  sonst mit der direkten Steuerung kollidieren (siehe oben).
- **Mehrdeutige Sensoren** (gleicher Name in mehreren Gruppen) werden nur im Vollabgleich-
  Intervall statt in Echtzeit aktualisiert.
- **WebSocket-Verfügbarkeit**: Nicht alle Enpal-Boxen unterstützen WebSocket. Die Integration
  erkennt das automatisch und fällt im Zweifelsfall auf HTML-Polling zurück.
- **Verbindungsstabilität**: Die WebSocket-Verbindung wird bei Abbruch automatisch neu
  aufgebaut; in seltenen Fällen kann es zu kurzen Aussetzern kommen.

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

## 🙏 Feedback erwünscht!

Als Beta-Version lebt diese Version von eurem Feedback. Besonders interessant:

- 📉 **CPU-Last der Enpal Box** — fällt sie nach dem Update spürbar geringer aus?
- ✅ Was funktioniert gut? ❌ Was funktioniert nicht?

Rückmeldungen bitte auf [GitHub Issues](https://github.com/derolli1976/enpal/issues) oder in den
[GitHub Discussions](https://github.com/derolli1976/enpal/discussions).
