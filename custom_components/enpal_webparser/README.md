# Enpal Webparser

Diese Home Assistant Integration liest Daten von einer lokalen Enpal-Webseite (z. B. `http://192.168.2.70/deviceMessages`) aus und stellt die Werte als Sensoren in Home Assistant zur Verfügung.

## 🔧 Funktionen

- Liest Messwerte aus HTML-Tabellen auf der lokalen Enpal-Geräteseite
- Automatische Gruppierung nach Datenbereich (z. B. Wallbox, Battery, Inverter)
- Sensor-Namen sind sprechend und gruppiert
- Auto-Aktualisierung über einstellbares Intervall
- Sensoren erscheinen automatisch in Home Assistant
- Nicht ausgewählte Gruppen werden als deaktivierte Entitäten angezeigt

## ⚙️ Konfiguration

Die Integration kann über die Benutzeroberfläche von Home Assistant konfiguriert werden:

- **URL der Datenquelle**: z. B. `http://192.168.2.70/deviceMessages`
- **Aktualisierungsintervall**: Zeit in Sekunden
- **Sensorgruppen**: Mehrfachauswahl wie `Wallbox`, `Battery`, `Inverter`, etc.

## 🧩 Installation

1. Kopiere den Ordner `custom_components/enpal_webparser/` in dein Home Assistant `custom_components` Verzeichnis.
2. Starte Home Assistant neu.
3. Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen** und wähle **Enpal Webparser**.
4. Gib die URL, Intervall und Gruppen an.

## 🐛 Probleme & Feedback

Bitte eröffne ein GitHub-Issue unter  
[https://github.com/yourname/enpal_webparser/issues](https://github.com/yourname/enpal_webparser/issues)

---
**Icon und Logo folgen bald. Farben orientieren sich an [enpal.de](https://www.enpal.de).**
