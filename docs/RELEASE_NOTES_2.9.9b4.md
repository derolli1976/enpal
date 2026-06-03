# 2.9.9b4 - Bessere Wallbox-Status-Erkennung & Reparatur-Meldung (Beta)

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

> **Die Echtzeit- und Wallbox-Funktionen setzen die Enpal-Firmware
> `Solar Rel. 8.50.1-773465 (27.05.2026)` voraus.**
>
> - Der **WebSocket-Modus** (Echtzeit-Daten) und die **native Wallbox-Steuerung ohne Add-on** funktionieren nur mit Firmware **8.50**.
> - Das **inkrementelle RenderBatch-Parsing** basiert auf dem Datenformat von Firmware **8.50**.
> - Auf älteren Firmware-Ständen bleibt der **HTML-Polling-Modus (Legacy)** nutzbar, ohne die neuen Echtzeit- und Wallbox-Funktionen.
> - Enpal verteilt die Firmware automatisch. Eine manuelle Auswahl ist nicht möglich.

---

## 🎉 Was ist neu in 2.9.9b4?

### Wallbox-Status wird zuverlässiger erkannt

**Das Problem:** Je nach Firmware liefert die Enpal Box den Wallbox-Status-Sensor unter
unterschiedlichen Namen. Auf manchen Boxen (z.B. Enpal ArC GEN2) heißt der Rohsensor
`Status.Connector.1` statt `Status.Wallbox.Connector.1`. Die automatische Erkennung hat diesen
Namen bisher nicht berücksichtigt, dadurch blieb `sensor.wallbox_status` dauerhaft `unknown`.

**Die Lösung:** Die automatische Erkennung berücksichtigt jetzt beide Namensvarianten. Auf den
betroffenen Boxen wird der Wallbox-Status ohne weitere Einstellungen korrekt angezeigt.

### Reparatur-Meldung bei fehlendem Status-Sensor

Falls die Box den Status-Sensor unter einem noch unbekannten Namen liefert, bleibt das Problem
nicht länger im Verborgenen:

- Ist die **Wallbox-Steuerung aktiv**, findet die Integration aber keinen passenden Status-Sensor,
  legt sie eine **Reparatur-Meldung** in Home Assistant an (**Einstellungen → System →
  Reparaturen**).
- Über **Beheben** öffnet sich ein Dialog, in dem du den richtigen Wallbox-Sensor direkt auswählst.
- Nach der Auswahl lädt die Integration neu und zeigt den Status an. Die Meldung verschwindet
  automatisch, sobald der Status-Sensor gefunden wird.

Die Meldung erscheint nur, wenn die Box tatsächlich Wallbox-Sensoren liefert, der Name aber nicht
zur automatischen Erkennung passt. Auf älteren Boxen ohne native Wallbox-Sensoren wird keine
Meldung angelegt.

---

## 🔧 Installation der Beta

### Über HACS:
1. In HACS → **Enpal Solar** öffnen
2. Auf die **drei Punkte** (⋮) klicken → **Version auswählen**
3. Version **2.9.9b4** auswählen und installieren
4. Home Assistant **neu starten**

### Bestehende Beta-Installation upgraden:
1. Version **2.9.9b4** über HACS installieren (siehe oben)
2. Home Assistant **neu starten**
3. Es sind keine Konfigurationsänderungen nötig. Bestehende Einstellungen bleiben erhalten.

---

## ⚠️ Bekannte Einschränkungen (Beta)

- **Firmware 8.50 nötig** für WebSocket-, Wallbox- und RenderBatch-Funktionen (siehe oben).
- **Wallbox App / Add-on im WebSocket-Modus deaktivieren.** Es wird nicht mehr gebraucht und kann sonst mit der direkten Steuerung kollidieren.
- **Mehrdeutige Sensoren** (gleicher Name in mehreren Gruppen) aktualisieren erst im Vollabgleich-Intervall statt in Echtzeit.
- **WebSocket-Verfügbarkeit:** Nicht alle Enpal-Boxen unterstützen WebSocket. Die Integration erkennt das automatisch und fällt im Zweifel auf HTML-Polling zurück.

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

- 🅿️ Wird der **Wallbox-Status** jetzt korrekt angezeigt?
- ✅ Was funktioniert gut? ❌ Was funktioniert nicht?

Rückmeldungen bitte auf [GitHub Issues](https://github.com/derolli1976/enpal/issues) oder in den
[GitHub Discussions](https://github.com/derolli1976/enpal/discussions).
