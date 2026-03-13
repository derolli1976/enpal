# 2.3.0 - Wärmepumpen-Unterstützung

## 🎉 Neue Funktion

**Wärmepumpen-Sensoren**: Die Integration unterstützt jetzt Sensoren für installierte Enpal-Wärmepumpen! Nach Aktivierung der Sensor-Gruppe werden alle verfügbaren Wärmepumpen-Sensoren automatisch in Home Assistant angelegt.

## 📊 Neue Sensoren

Die folgenden Wärmepumpen-Sensoren werden unterstützt (je nach vorhandener Hardware):

- **Heatpump DomesticHotWater Temperature**: Warmwasser-Temperatur
- **Heatpump Outside Temperature**: Außentemperatur
- **Heatpump Power Consumption Total**: Aktuelle Leistungsaufnahme (kW)
- **Heatpump Energy Consumption Total Lifetime**: Gesamter Energieverbrauch seit Installation (kWh)
- **Heatpump Operation Mode Midea**: Betriebsmodus der Wärmepumpe

Alle Sensoren werden mit passenden Icons und korrekten Device Classes sowie State Classes angelegt (z.B. Energy-Sensor als `total_increasing` für das HA Energy Dashboard).

## 🔧 Aktivierung

**Wichtig**: Die Wärmepumpen-Sensoren müssen explizit aktiviert werden:

1. **Einstellungen** → **Geräte & Dienste** öffnen
2. **Enpal Webparser** Integration suchen
3. Auf das **Zahnrad** (Konfigurieren) klicken
4. Bei der Sensor-Gruppen-Auswahl den **Haken bei "Heatpump"** setzen
5. Mit **Senden** bestätigen
6. Home Assistant neu laden (oder auf den nächsten Update-Zyklus warten)

Die Sensoren erscheinen anschließend automatisch unter dem Enpal-Gerät.

## 🎯 Betroffene Systeme

Relevant für alle Enpal-Anlagen mit installierter Wärmepumpe. Installationen ohne Wärmepumpe bleiben unverändert.

## 📋 Update-Hinweise

1. Auf Version 2.3.0 aktualisieren (über HACS)
2. Home Assistant neu starten
3. Wärmepumpen-Sensoren wie oben beschrieben aktivieren

**Hinweis**: Die Integration prüft automatisch, ob die Enpal-Box Wärmepumpen-Daten bereitstellt. Ohne vorhandene Wärmepumpe werden auch keine Sensoren erstellt.

## ℹ️ Kompatibilität

Keine Breaking Changes. Alle bestehenden Sensoren und historischen Daten bleiben unverändert.

**Rückwärtskompatibel**: Bestehende Installationen ohne Wärmepumpe sind nicht betroffen.

## 🧪 Getestet mit

- Enpal-Anlagen mit Wärmepumpe (reale Daten)
- Verschiedenen Sensor-Gruppen-Kombinationen
- Encoding-Probleme in Temperatur-Werten wurden berücksichtigt

## 🙏 Danke

Vielen Dank an die Community für die Anfrage nach Wärmepumpen-Unterstützung und das bereitgestellte Test-HTML!

Feedback, Verbesserungsvorschläge oder Fehlermeldungen können auf [GitHub](https://github.com/derolli1976/enpal) oder in den Diskussionen gemeldet werden.

---

## 🔍 Technische Details

- 5 neue Heatpump-Sensoren mit individuellen Icons (mdi:water-thermometer, mdi:heat-pump, etc.)
- Automatische Erkennung des korrekten State Class (measurement für Power, total_increasing für Energy)
- Robustes Parsing auch bei Encoding-Problemen in den Rohdaten
- Vollständige Test-Abdeckung mit Real-World-HTML-Fixtures
