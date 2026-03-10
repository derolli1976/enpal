# Wärmepumpen-Support testen 🧪

Diese Anleitung hilft dir, die neue Wärmepumpen-Unterstützung in deiner Home Assistant Installation zu testen.

## 🎯 Was wird getestet?

Die Integration kann jetzt Wärmepumpen-Sensoren von deiner Enpal-Anlage auslesen, falls eine Wärmepumpe installiert ist.

## ⚠️ Voraussetzungen

- Du hast eine Enpal-Wärmepumpe installiert
- Die Wärmepumpe erscheint auf der `/deviceMessages` Seite deiner Enpal Box als "Heatpump"-Block
- Du hast das **File Editor** oder **Studio Code Server** Add-on in Home Assistant installiert

### Add-on installieren (falls noch nicht vorhanden)

**File Editor** (einfacher):
1. Einstellungen → Add-ons → Add-on Store
2. Suche nach "File editor"
3. Installiere "File editor" von Home Assistant Community Add-ons
4. Klicke auf "START"
5. Optional: Aktiviere "Show in sidebar"

**ODER Studio Code Server** (erweitert):
1. Einstellungen → Add-ons → Add-on Store
2. Suche nach "Studio Code Server"
3. Installiere "Studio Code Server"
4. Klicke auf "START"
5. Optional: Aktiviere "Show in sidebar"

## 📝 Dateien bearbeiten

### Schritt 1: Editor öffnen

**File Editor:**
- Klicke in der Sidebar auf "File editor"
- Oder gehe zu: Einstellungen → Add-ons → File editor → "OPEN WEB UI"

**Studio Code Server:**
- Klicke in der Sidebar auf "Studio Code Server"
- Oder gehe zu: Einstellungen → Add-ons → Studio Code Server → "OPEN WEB UI"

### Schritt 2: const.py öffnen

Navigiere im Editor zu:
```
config/custom_components/enpal_webparser/const.py
```

**File Editor:** Nutze den Ordner-Browser links  
**Studio Code Server:** Nutze den Explorer (Strg+Shift+E)

### Schritt 3: Heatpump-Gruppe hinzufügen

Suche nach der Zeile mit `DEFAULT_GROUPS = [` (ca. **Zeile 27**).

**Vorher:**
```python
DEFAULT_GROUPS = [
    "Wallbox",
    "Battery",
    "Inverter",
    "Site Data",
    "IoTEdgeDevice",
    "PowerSensor",
]
```

**Nachher:**
```python
DEFAULT_GROUPS = [
    "Wallbox",
    "Battery",
    "Inverter",
    "Site Data",
    "IoTEdgeDevice",
    "PowerSensor",
    "Heatpump",  # <-- NEU HINZUGEFÜGT
]
```

⚠️ **Wichtig:** Das Komma nach `"PowerSensor",` muss bleiben!

### Schritt 4: Icons hinzufügen (optional, aber empfohlen)

Scrolle runter bis zu `ICON_MAP = {` (ca. **Zeile 230**).

Scrolle bis fast zum Ende der Icon-Liste, **DIREKT VOR** das schließende `}`.

Füge **nach** den Inverter System State Icons, aber **VOR** dem `}` diese Zeilen ein:

```python
    # Inverter System State bits (letzte Zeile)
    "inverter_system_state_spot_check": "mdi:magnify",

    # Heatpump  <-- NEU HINZUFÜGEN
    "heatpump_domestichotwater_temperature": "mdi:water-thermometer",
    "heatpump_energy_consumption_total_lifetime": "mdi:lightning-bolt",
    "heatpump_operation_mode_midea": "mdi:heat-pump-outline",
    "heatpump_outside_temperature": "mdi:thermometer",
    "heatpump_power_consumption_total": "mdi:heat-pump",
}  # <-- Hier ist das schließende }
```

⚠️ **Wichtig:** Nach jeder Zeile muss ein Komma `,` stehen (außer beim `}`).

### Schritt 5: Datei speichern

**File Editor:**
- Klicke oben rechts auf das **Speichern-Symbol** (💾)
- Oder nutze `Strg+S` (Windows/Linux) bzw. `Cmd+S` (Mac)

**Studio Code Server:**
- Datei → Speichern
- Oder nutze `Strg+S` (Windows/Linux) bzw. `Cmd+S` (Mac)

## 🔄 Integration aktivieren

1. **Home Assistant neu starten**
   - Einstellungen → System → Neu starten
   - ⚠️ Wichtig: Ein kompletter Neustart ist erforderlich, nicht nur Integration neu laden!

2. **Warte bis Home Assistant vollständig gestartet ist** (1-2 Minuten)

3. **Öffne die Enpal Integration:**
   - Einstellungen → Geräte & Dienste → Enpal Solar Integration
   - Klicke auf **"Konfigurieren"** oder die 3 Punkte → **"Neu konfigurieren"**

4. **Aktiviere die Heatpump-Gruppe:**
   - Im Konfigurationsdialog findest du **"Sensorgruppen auswählen"**
   - Setze das Häkchen bei **"Heatpump"** ✓
   - Klicke auf **"Absenden"**

5. **Warte 1-2 Minuten**, bis die Integration die Daten aktualisiert hat

## ✅ Überprüfung

### Schritt 1: Prüfe ob die Sensoren erscheinen

Gehe zu: **Einstellungen → Geräte & Dienste → Enpal Solar Integration → Gerät**

Du solltest neue Sensoren sehen:
- `sensor.heatpump_domestichotwater_temperature` (Warmwassertemperatur)
- `sensor.heatpump_energy_consumption_total_lifetime` (Gesamtverbrauch)
- `sensor.heatpump_operation_mode_midea` (Betriebsmodus)
- `sensor.heatpump_outside_temperature` (Außentemperatur)
- `sensor.heatpump_power_consumption_total` (Aktuelle Leistung)

### Schritt 2: Überprüfe die Werte

Klicke auf einen der Sensoren und prüfe:
- ✅ Hat der Sensor einen aktuellen Wert?
- ✅ Erscheint ein Icon (z.B. Thermometer, Wärmepumpe)?
- ✅ Ist die Einheit korrekt (°C, kWh, kW)?
- ✅ Wird der Wert regelmäßig aktualisiert?

### Schritt 3: Vergleich mit Enpal Box

Öffne in einem Browser:
```
http://<deine-enpal-box-ip>/deviceMessages
```

Scrolle zum **"Heatpump"** Block und vergleiche die Werte:
- Stimmen die Werte in Home Assistant mit denen auf der Webseite überein? ✓

## 📊 Beispiel: Dashboard Card erstellen

Teste die Sensoren mit einer einfachen Dashboard-Card:

```yaml
type: entities
title: Wärmepumpe
entities:
  - entity: sensor.heatpump_power_consumption_total
    name: Aktuelle Leistung
  - entity: sensor.heatpump_domestichotwater_temperature
    name: Warmwasser
  - entity: sensor.heatpump_outside_temperature
    name: Außentemperatur
  - entity: sensor.heatpump_energy_consumption_total_lifetime
    name: Gesamtverbrauch
```

## 🐛 Problem-Behandlung

### Sensoren erscheinen nicht

1. **Prüfe die Logs:**
   - Einstellungen → System → Protokolle
   - Suche nach `[Enpal]`
   
2. **Überprüfe die Enpal Box:**
   - Öffne `http://<deine-enpal-box-ip>/deviceMessages`
   - Gibt es einen "Heatpump" Block?
   - Sind darin Sensoren sichtbar?

3. **Integration komplett neu laden:**
   - Einstellungen → Geräte & Dienste → Enpal → Neu laden
   - Warte 2 Minuten

### Fehlermeldungen nach dem Speichern

Wenn du Fehler in den Logs siehst:
1. **Prüfe die Syntax in const.py:**
   - Sind alle Kommas an der richtigen Stelle?
   - Sind die Anführungszeichen korrekt?
   - Ist das schließende `}` noch vorhanden?

2. **Fehlermeldung notieren** und unten im Feedback teilen

## 🔙 Rollback (falls Probleme auftreten)

Falls etwas nicht funktioniert, kannst du die Integration einfach über HACS neu installieren:

1. **Einstellungen → HACS → Integrationen**
2. Suche nach **"Enpal Solar Integration"**
3. Klicke auf die 3 Punkte → **"Neu herunterladen"**
4. Bestätige mit **"Herunterladen"**
5. **Home Assistant neu starten**

Die originale Version wird wiederhergestellt und deine Konfiguration bleibt erhalten.

## 📝 Feedback

Nach dem Test, bitte melde zurück:

✅ **Was funktioniert:**
- Welche Sensoren erscheinen?
- Sind die Werte korrekt?
- Funktionieren die Icons?

❌ **Was funktioniert nicht:**
- Welche Sensoren fehlen?
- Gibt es Fehlermeldungen? (bitte Logs beifügen)
- Stimmen die Werte nicht?

📸 **Hilfreich wären:**
- Screenshot vom Heatpump-Block auf `/deviceMessages`
- Screenshot der Sensoren in Home Assistant
- Auszug aus den Home Assistant Logs mit `[Enpal]`

## 🙏 Danke!

Vielen Dank fürs Testen! Dein Feedback hilft, die Integration für alle Wärmepumpen-Nutzer zu verbessern.

Bei Fragen oder Problemen: [GitHub Issues](https://github.com/derolli1976/enpal/issues)
