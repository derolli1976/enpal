<p align="center">
  <img src="https://raw.githubusercontent.com/derolli1976/enpal/main/brands/enpal_webparser/logo.png" alt="Enpal Solar Logo" width="250"/>
</p>

# Enpal Solar – Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![HACS installs](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.enpal_webparser.total)](https://github.com/derolli1976/enpal)
[![GitHub release](https://img.shields.io/github/release/derolli1976/enpal.svg)](https://github.com/derolli1976/enpal/releases)
[![hacs_install](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=derolli1976&repository=enpal&category=integration)

<a href="https://buymeacoffee.com/derolli1976" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>

Diese Home Assistant Integration liest Daten von der lokalen Enpal-Webseite der Solaranlage (z. B. `http://192.168.178.178/deviceMessages`) aus und stellt die Werte als Sensoren in Home Assistant zur Verfügung.  
Getestet mit Version 2 der Enpal Box und Solar Rel. 8.46.4-355926 (21.05.2025).

### ⚠️ Hinweis: Einige Enpal Boxen der **1. Generation** werden **unterstützt**.  
Entscheidend ist, ob unter der IP-Adresse der Enpal Box im lokalen Netzwerk eine Webseite wie die folgende angezeigt wird:

<p align="left">
  <img src="./images/enpal_box_webseite.png" alt="Enpal Box Webseite" width="600"/>
</p>

---

## 🔧 Funktionen

- Liest Messwerte aus HTML-Tabellen auf der lokalen Enpal-Geräteseite
- Automatische Gruppierung nach Datenbereich (z. B. Wallbox, Battery, Inverter)
- Sprechende, gruppierte Sensor-Namen
- Automatische Aktualisierung über einstellbares Intervall
- Sensoren erscheinen automatisch in Home Assistant
- Nicht ausgewählte Gruppen werden als deaktivierte Entitäten angelegt
- Konfiguration vollständig über das Home Assistant UI möglich
- **NEU**: Experimentelle Wallbox-Steuerung über optionales Add-on

---

## ⚙️ Konfiguration

Die Integration kann vollständig über das Home Assistant UI konfiguriert werden:

- **URL der Datenquelle**: z. B. `http://192.168.178.178/deviceMessages`
- **Aktualisierungsintervall**: in Sekunden
- **Sensorgruppen**: Auswahl von Bereichen wie `Wallbox`, `Battery`, `Inverter`, etc.
- **Wallbox-Steuerung aktivieren**: Optional, wenn Add-on installiert

---

## 📦 Installation

### 🧩 Variante 1: Installation über HACS (empfohlen)

Diese Integration ist **offiziell in HACS gelistet** – ein manuelles Hinzufügen ist **nicht mehr nötig**.

#### Schritt-für-Schritt:

1. Öffne **HACS** über die Seitenleiste in Home Assistant  
2. Gib im Suchfeld oben einfach **Enpal Solar** ein  
3. Wähle die Integration aus der Liste aus  
4. Klicke auf **„Installieren“**  
5. Starte Home Assistant neu  
6. Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen**  
7. Suche nach **Enpal Solar** und folge dem Konfigurationsdialog (z. B. URL, Intervall, Sensorgruppen)

> 💡 **Hinweis:** Installierte Integrationen erscheinen automatisch unter **Einstellungen → Geräte & Dienste**. Auch Updates und Reparaturhinweise werden dort angezeigt.

---

### 🛠️ Variante 2: Manuelle Installation

1. Lade das Repository herunter oder klone es  
2. Kopiere den Ordner `custom_components/enpal_webparser/` in dein Home Assistant `custom_components` Verzeichnis  
3. Starte Home Assistant neu  
4. Füge die Integration wie oben beschrieben hinzu

---

## 🚗 Wallbox Add-on (Optional & Experimentell)

Zur Steuerung einer Enpal Wallbox wird dieses Add-on benötigt:  
🔗 [https://github.com/derolli1976/enpal-wallbox-addon](https://github.com/derolli1976/enpal-wallbox-addon)

### 🔌 Add-on Installation

1. Öffne den **Add-on Store** in Home Assistant  
2. Gehe zum Drei-Punkte-Menü (oben rechts) → **Repositories**  
3. Füge folgendes Repository hinzu:

