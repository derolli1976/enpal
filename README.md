# Enpal Webparser – Home Assistant Integration

Dieses Projekt stellt eine benutzerdefinierte [Home Assistant](https://www.home-assistant.io/) Integration bereit, die Daten von einer lokalen Enpal-Weboberfläche ausliest (z. B. `http://192.168.1.24/deviceMessages`) und als Sensoren in Home Assistant verfügbar macht.

## 🧩 Funktionen

- Automatischer Abruf von Messwerten aus der HTML-Oberfläche der Enpal-Anlage
- Unterstützung mehrerer Datenbereiche: Wallbox, Battery, Inverter, IoTEdgeDevice usw.
- Dynamische Sensorerzeugung mit sprechenden Namen
- UI-basierte Konfiguration (URL, Aktualisierungsintervall, Gruppenwahl)
- Sensoren können gruppenweise deaktiviert werden
- Vollständig HACS-kompatibel

## 📦 Installation

1. Füge dieses Repository in Home Assistant HACS als benutzerdefiniertes Repository hinzu:
   - Typ: **Integration**
   - URL: `https://github.com/derolli1976/enpal`
2. Suche nach „Enpal Webparser“ in HACS und installiere es
3. Nach dem Neustart von Home Assistant:
   - Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen**
   - Wähle **Enpal Webparser**
   - Gib die gewünschte URL, das Intervall und die gewünschten Gruppen an

## ⚙️ Konfiguration

Die Konfiguration erfolgt vollständig über die Benutzeroberfläche von Home Assistant.  
Die folgenden Optionen stehen zur Verfügung:

| Option       | Beschreibung                                      |
|--------------|---------------------------------------------------|
| **URL**      | Adresse der lokalen Enpal-Webseite               |
| **Intervall**| Aktualisierungsintervall in Sekunden             |
| **Gruppen**  | Auswahl der Sensorgruppen (z. B. „Wallbox“)      |

## 🖼️ Beispielhafte Sensoren

- `Wallbox: Current Connector 1 (Phase B)`
- `Battery: Energy Battery Discharge Day`
- `Inverter: Voltage Phase (C)`

## 💡 Hinweise

- Diese Integration verwendet HTML-Scraping der Enpal-Webseite – keine offizielle API.
- Die Werte werden lokal verarbeitet – kein Cloudzugriff notwendig.
- Farbgebung und Stil orientieren sich an [https://www.enpal.de](https://www.enpal.de)

## 🛠️ Entwicklung

Pull Requests sind willkommen!  
Bitte melde Bugs oder Ideen unter:  
👉 [Issue Tracker](https://github.com/derolli1976/enpal/issues)

---

**Lizenz:** MIT  
Dieses Projekt steht in keinem offiziellen Zusammenhang mit Enpal.
