# 3.2.9b1 - Eigene Geräte für Wechselrichter, Batterie & Co. (Issue #192)

Dieses Beta-Release teilt die Integration in mehrere Geräte auf, benennt das Hauptgerät in "Enpal Box" um und ordnet die Integration der neuen Home-Assistant-Kategorie "Energie" zu.

---

## ✨ Neu: Aufteilung in mehrere Geräte (Issue #192)

### Das Problem

Bisher lagen alle Entitäten auf einem einzigen Gerät. Einen Bereich konnte man deshalb nur für alles gemeinsam setzen: Wechselrichter, Batterie und Wallbox landeten zusammen im Heizungsraum. Wer die Wallbox in der Garage haben wollte, musste jede einzelne Entität umstellen.

### Die Lösung

Wechselrichter, Batterie, Wallbox, Wärmepumpe und Stromsensor sind jetzt eigene Geräte. Sie sind in Home Assistant als "Verbunden über Enpal Box" mit dem Hauptgerät verknüpft und können jeweils einem eigenen Bereich zugeordnet werden.

| Gerät | Enthält |
|---|---|
| **Enpal Box** | Site Data, IoTEdgeDevice, ControlBox |
| **Wechselrichter** | Inverter-Sensoren inkl. der berechneten DC-Energiezähler |
| **Batterie** | Battery-Sensoren |
| **Wallbox** | Wallbox-Sensoren, Schalter, Buttons und Modus-Auswahl |
| **Wärmepumpe** | Heatpump-Sensoren |
| **Stromsensor** | PowerSensor-Sensoren |

Neue Geräte übernehmen beim ersten Start einmalig den Bereich der Enpal Box. Danach können sie frei zugeordnet werden.

### ⚠️ Bitte prüfen: Automationen mit Geräte-Ziel

**Entity-IDs bleiben unverändert**, Historie, Statistiken und Automationen auf Entitäten funktionieren weiter.

Automationen, Skripte und Dashboard-Karten, die als Ziel das **Gerät** "Enpal Box" (bisher "Enpal Webgerät") verwenden, erreichen die verschobenen Entitäten nicht mehr. Bitte diese auf das neue Gerät (z. B. "Wallbox") oder direkt auf die Entität umstellen.

## ✏️ Umbenennung: "Enpal Webparser" → "Enpal Box"

Der ursprüngliche Projektname taucht in der Oberfläche nicht mehr auf:

- Das Hauptgerät heißt jetzt "Enpal Box" (bisher "Enpal Webgerät", Modell "Webparser").
- Der Integrations-Eintrag wird von "Enpal Webparser" in "Enpal Box" umbenannt. Wurde der Eintrag selbst umbenannt, bleibt der eigene Name erhalten.

Die interne Domain `enpal_webparser` bleibt unverändert, es ist keine Neueinrichtung nötig.

## 🏷️ Integrations-Kategorie

Die Integration ist jetzt der Kategorie **Energie › Solar & Batterien** zugeordnet und wird in Home Assistant und im Marketplace dort einsortiert.

## 🔄 Kompatibilität

- **Neue Mindestversion: Home Assistant 2024.3.0** (benötigt für übersetzte Gerätenamen)
- Keine Änderungen an Entity-IDs
- WebSocket-, HTML- und InfluxDB-Modus bleiben unverändert
- Enthält alle Änderungen aus 3.2.0

## 🧪 Beta-Hinweis

Rückmeldungen zur neuen Geräteaufteilung sind willkommen, am besten als [GitHub Issue](https://github.com/derolli1976/enpal/issues).

## ❤️ Unterstützung

Wenn dir die Integration hilft und du die Weiterentwicklung unterstützen möchtest, freue ich mich über eine Spende über die **Sponsoring-Sektion** dieses Repositories (Button "Sponsor" oben auf der [Projektseite](https://github.com/derolli1976/enpal)) oder über [Buy Me a Coffee](https://buymeacoffee.com/derolli1976). Danke!
