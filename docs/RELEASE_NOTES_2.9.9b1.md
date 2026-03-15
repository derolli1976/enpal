# 2.9.9b1 - WebSocket & Native Wallbox-Steuerung (Beta)

---

## ⚠️ BETA-VERSION — WICHTIGE HINWEISE

> **Dies ist eine Beta-Version und NICHT für den produktiven Einsatz gedacht!**
>
> - 🧪 **Nur zum Testen** — diese Version kann noch Fehler enthalten.
> - 💾 **Backup erstellen!** — Vor der Installation unbedingt ein Home Assistant-Backup anlegen.
> - 🔄 **Downgrade möglich** — Bei Problemen kann jederzeit auf die stabile Version 2.3.0 zurückgewechselt werden (über HACS → Version auswählen).
> - 🐛 **Fehler melden** — Bitte Fehler und Auffälligkeiten auf [GitHub Issues](https://github.com/derolli1976/enpal/issues) melden, damit wir sie vor dem stabilen Release beheben können.
> - 📊 **Historische Daten** — Beim Wechsel der Datenquelle (HTML → WebSocket) können sich Sensor-IDs ändern. Bestehende Historien-Daten bleiben erhalten, aber neue Sensoren starten ohne Historie.

---

## 🎉 Neue Funktionen

### 1. WebSocket-Verbindung (Echtzeit-Daten)

**Was ist das?**
Bisher hat die Integration regelmäßig die Webseite der Enpal Box abgefragt und die dort angezeigten Daten ausgelesen (sogenanntes "HTML-Scraping"). Das funktioniert, ist aber langsam und kann bei Änderungen an der Webseite brechen.

Die neue WebSocket-Verbindung nutzt stattdessen die **native Schnittstelle** der Enpal Box — dieselbe Technik, die auch die Weboberfläche intern verwendet. Die Daten werden dabei **direkt und in Echtzeit** an Home Assistant übertragen.

**Vorteile auf einen Blick:**
- ⚡ **Schnellere Updates** — Sensor-Werte werden sofort aktualisiert, statt nur alle 60 Sekunden
- 🔒 **Stabiler** — Keine Abhängigkeit von der HTML-Struktur der Webseite
- 📉 **Weniger Systemlast** — Eine dauerhafte Verbindung statt ständiger Seitenaufrufe
- 📊 **Mehr Sensoren** — Die WebSocket-API liefert zusätzliche aggregierte Werte (z.B. Tagesverbrauch, Gesamthausleistung)

### 2. Native Wallbox-Steuerung (ohne Add-on!)

**Was ist das?**
Bisher war zum Steuern der Wallbox ein separates Home Assistant Add-on nötig, das als Vermittler zwischen Home Assistant und der Enpal Box fungierte. Das war umständlich einzurichten und eine zusätzliche Fehlerquelle.

**Neu: Direkte Wallbox-Steuerung** — Im WebSocket-Modus kommuniziert die Integration jetzt **direkt** mit der Wallbox-Seite der Enpal Box. Das separate Wallbox Add-on wird im WebSocket-Modus **nicht mehr benötigt**!

**Vorteile auf einen Blick:**
- 🚫 **Kein Extra-Add-on nötig** — Weniger Abhängigkeiten, einfachere Installation
- ⚡ **Schnellere Reaktion** — Direkter Befehlsweg ohne Umweg über ein Add-on
- 🔧 **Einfachere Einrichtung** — Wallbox-Steuerung einfach in den Integrationseinstellungen aktivieren
- 🔄 **Zuverlässiger** — Keine Probleme mehr durch Add-on-Abstürze oder -Updates

**Unterstützte Wallbox-Funktionen:**
- Laden starten / stoppen
- Lademodus wechseln: Eco, Solar, Full, Smart
- Wallbox-Status auslesen (Modus, Verbindungsstatus)

### 3. Automatische Erkennung der besten Datenquelle

Bei der Einrichtung erkennt die Integration automatisch, ob die Enpal Box WebSocket unterstützt. Du musst dich nicht mit technischen Details befassen — die Integration wählt selbst die beste verfügbare Methode:

- **Auto-detect (empfohlen)** — Prüft automatisch, ob WebSocket verfügbar ist
- **WebSocket (Echtzeit)** — Erzwingt die neue WebSocket-Verbindung
- **HTML-Polling (Legacy)** — Nutzt die bisherige Methode (für ältere Enpal-Boxen)

---

## 🔧 Installation der Beta

### Über HACS:
1. In HACS → **Enpal Solar** öffnen
2. Auf die **drei Punkte** (⋮) klicken → **Version auswählen**
3. Version **2.9.9b1** auswählen und installieren
4. Home Assistant **neu starten**

### Ersteinrichtung:
Die Integration erkennt beim Einrichten automatisch die beste Datenquelle. Es sind keine speziellen Einstellungen nötig.

### Bestehende Installation upgraden:
1. Beta-Version über HACS installieren (siehe oben)
2. Home Assistant neu starten
3. **Einstellungen** → **Geräte & Dienste** → **Enpal Webparser** → **Konfigurieren**
4. Bei **Datenquelle** die gewünschte Option wählen (oder "Auto-detect" belassen)
5. Ggf. **Wallbox-Steuerung aktivieren** (erfordert im HTML-Modus weiterhin das Add-on)
6. Speichern — die Integration lädt automatisch neu

---

## ⚠️ Bekannte Einschränkungen (Beta)

- **WebSocket-Verfügbarkeit**: Nicht alle Enpal-Boxen unterstützen WebSocket. Die Integration erkennt das automatisch und fällt im Zweifelsfall auf HTML-Polling zurück.
- **Sensor-Unterschiede**: Im WebSocket-Modus stehen teilweise andere Sensoren zur Verfügung als im HTML-Modus (ca. 88 gemeinsame Sensoren, 45 nur in HTML, 18 nur in WebSocket). Siehe [Sensor-Vergleich](SENSOR_COMPARISON.md) für Details.
- **Wallbox-Steuerung**: Die native Wallbox-Steuerung wurde mit begrenzter Hardware-Vielfalt getestet. Bitte Rückmeldung geben, ob alles funktioniert!
- **Verbindungsstabilität**: Die WebSocket-Verbindung wird automatisch bei Abbruch neu aufgebaut. In seltenen Fällen kann es zu kurzen Aussetzern kommen.

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

- **Rückwärtskompatibel**: Bestehende Installationen werden automatisch migriert. Die Datenquelle wird auf "HTML" gesetzt, damit alles wie gewohnt funktioniert.
- **Wallbox Add-on**: Im HTML-Modus wird das Add-on weiterhin benötigt. Nur im WebSocket-Modus entfällt das Add-on.
- **Keine Breaking Changes**: Bestehende Sensoren und historische Daten bleiben unverändert.

---

## 🙏 Feedback erwünscht!

Als Beta-Version lebt diese Version von eurem Feedback. Bitte meldet:

- ✅ Was funktioniert gut?
- ❌ Was funktioniert nicht?
- 💡 Was fehlt oder könnte verbessert werden?

Rückmeldungen bitte auf [GitHub Issues](https://github.com/derolli1976/enpal/issues) oder in den [GitHub Discussions](https://github.com/derolli1976/enpal/discussions).

Vielen Dank an alle Tester! 🎉

---

## 🔍 Technische Details

- Blazor SignalR WebSocket-Protokoll mit MessagePack-Encoding
- Abstrakte API-Schicht (`EnpalApiClient`) für austauschbare Datenquellen
- `EnpalWebSocketClient` für Echtzeit-Daten, `EnpalHtmlClient` als Legacy-Wrapper
- `WallboxBlazorClient` für direkte Wallbox-Steuerung über die `/wallbox`-Seite
- Automatische Reconnect-Logik mit Keep-Alive-Pings
- Config Flow mit Auto-Detection, manueller Auswahl und Options Flow
- Automatische Migration bestehender Konfigurationen (inkl. Umbenennung `use_wallbox_addon` → `use_wallbox`)
- Credits: WebSocket-Protokoll basiert auf dem Reverse-Engineering von @arigon
