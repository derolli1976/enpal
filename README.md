<p align="center">
  <img src="https://raw.githubusercontent.com/derolli1976/enpal/main/brands/enpal_webparser/logo.png" alt="Enpal Solar Logo" width="250"/>
</p>

# Enpal Solar – Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/derolli1976/enpal.svg)](https://github.com/derolli1976/enpal/releases)
<a href="https://buymeacoffee.com/derolli1976" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>

Diese Home Assistant Integration liest Daten von der lokalen Enpal-Webseite der Solaranlage (z. B. `http://192.168.178.178/deviceMessages`) aus und stellt die Werte als Sensoren in Home Assistant zur Verfügung.  
Getestet mit der Version 2 der Enpal Box und Solar Rel. 8.45.3-322763 (08.04.2025).

---

## 🔧 Funktionen

- Liest Messwerte aus HTML-Tabellen auf der lokalen Enpal-Geräteseite
- Automatische Gruppierung nach Datenbereich (z. B. Wallbox, Battery, Inverter)
- Sensor-Namen sind sprechend und gruppiert
- Auto-Aktualisierung über einstellbares Intervall
- Sensoren erscheinen automatisch in Home Assistant
- Nicht ausgewählte Gruppen werden als deaktivierte Entitäten angezeigt
- Integration vollständig konfigurierbar über das Home Assistant UI (auch nachträglich)

---

## ⚙️ Konfiguration

Die Integration kann über die Benutzeroberfläche von Home Assistant konfiguriert werden:

- **URL der Datenquelle**: z. B. `http://192.168.178.178/deviceMessages`
- **Aktualisierungsintervall**: Zeit in Sekunden
- **Sensorgruppen**: Mehrfachauswahl wie `Wallbox`, `Battery`, `Inverter`, etc.

---

## 📦 Installation

### ✅ Variante 1: Manuell

1. Kopiere den Ordner `custom_components/enpal_webparser/` in dein Home Assistant `custom_components` Verzeichnis.
2. Starte Home Assistant neu.
3. Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen** und wähle **Enpal Solar**.
4. Gib die URL, das Intervall und gewünschte Gruppen an.

### 🧩 Variante 2: HACS (Custom Repository)

1. Öffne HACS in Home Assistant.
2. Klicke auf **"Integrationen" → "Benutzerdefiniertes Repository hinzufügen"** (oben rechts: 3-Punkte-Menü).
3. Gib die GitHub-URL dieses Repos ein:  
   `https://github.com/derolli1976/enpal`
4. Wähle als Typ **"Integration"**.
5. Installiere die Integration direkt über HACS.
6. Starte Home Assistant neu.
7. Füge die Integration wie gewohnt über das UI hinzu.

---

## ❓ FAQ & Hilfe

Antworten auf häufige Fragen findest du hier:  
📘 [FAQ – Häufige Fragen zur Enpal Solar Integration](https://github.com/derolli1976/enpal/wiki/FAQ)

---

## 🐛 Probleme & Feedback

Bitte eröffne ein GitHub-Issue unter:  
👉 [https://github.com/derolli1976/enpal/issues](https://github.com/derolli1976/enpal/issues)

---

## ⚠️ Disclaimer

Dieses Projekt steht in **keinerlei Verbindung zur Enpal B.V.**  
Es handelt sich um eine **inoffizielle, private Integration**, die auf öffentlich zugänglichen HTML-Daten basiert, die lokal im Netzwerk bereitgestellt werden.

Die Nutzung erfolgt auf **eigene Verantwortung**.  
Funktionen können durch Firmware- oder UI-Änderungen von Enpal jederzeit beeinträchtigt werden.

---
