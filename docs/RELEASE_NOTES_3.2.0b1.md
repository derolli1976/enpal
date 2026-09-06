# 3.2.0b1 - Neue Datenquelle: InfluxDB (Beta)

Dieses Beta-Release bringt eine dritte Datenquelle: Die Integration kann die Messwerte direkt aus der InfluxDB der Enpal Box lesen. Die Datenbank läuft auf jeder Box und wird von Enpal selbst befüllt. Der Zugriff erfordert einen Token, den Enpal auf Anfrage mitteilt.

---

## ✨ Neu: Datenquelle InfluxDB (Experten-Option)

### Was es bringt

Der InfluxDB-Modus liest die Werte direkt aus der Datenbank der Box, nicht aus der Weboberfläche. Er ist damit unabhängig von den Umbauten, die Enpal an der Webseite vornimmt. Die Firmware-Updates 8.50 und 8.51 haben gezeigt, wie oft solche Umbauten die Integration treffen können.

- Gleiche Entity-IDs wie im WebSocket-Modus. Ein Wechsel der Datenquelle erzeugt keine neuen Entitäten, Historie und Automationen bleiben erhalten.
- Einheiten kommen sauber aus der Datenbank (inklusive Wh-zu-kWh-Umrechnung wie bisher).
- Die Wallbox wird wie im WebSocket-Modus nativ gesteuert, ohne Add-on.
- Abfrage im eingestellten Intervall über eine einzelne Datenbank-Query. Keine zusätzlichen Abhängigkeiten.

### Was du brauchst

1. Öffne ein Ticket über den **Enpal Chatbot in der Enpal App** und frage den **InfluxDB-Zugriffstoken** und die **Organisation** für deine Box an.
2. Wähle im Setup oder in den Optionen der Integration die Datenquelle **"InfluxDB (expert, token required)"** und speichere.
3. Trage in den neu erscheinenden Feldern den Token ein. Organisation (`enpal`) und Bucket (`solar`) sind vorbelegt und passen in der Regel.

Die Integration prüft die Verbindung beim Speichern und zeigt eine verständliche Fehlermeldung, wenn Token oder Organisation nicht stimmen.

### Einschränkungen

- Die Datenbank enthält nur Zahlenwerte. Textsensoren wie Seriennummern oder Gerätenamen gibt es in diesem Modus nicht. Der Wallbox-Status kommt weiterhin über die Weboberfläche der Box.
- Der System-Status des Inverters liegt in der Datenbank nur als Zahl vor. Die Integration leitet die bekannten Einzelsensoren (Decimal, Flags, einzelne Bits) daraus ab.
- Die automatische Erkennung der Datenquelle wählt InfluxDB nie von selbst. Der Modus ist eine bewusste Entscheidung.

### Warum "Experten-Option"?

Der Modus braucht einen Token, den du aktiv bei Enpal anfragen musst. Genau daran sind früher viele Setups gescheitert, deshalb war der InfluxDB-Zugriff bisher bewusst nicht eingebaut. Wer den Token hat, bekommt jetzt einen robusten dritten Weg.

## 🧪 Beta-Hinweis

Getestet gegen eine Box mit Firmware Solar Rel. 8.51.1 und InfluxDB 2.8.0 (Huawei-System, 124 Sensoren). Rückmeldungen von FoxESS-Systemen und anderen Konstellationen sind willkommen, am besten als [GitHub Issue](https://github.com/derolli1976/enpal/issues).

## 🔄 Kompatibilität

- Keine Änderungen an bestehenden Entity-IDs, Sensoren oder Optionen
- WebSocket- und HTML-Modus bleiben unverändert
- Enthält alle Fixes aus 3.1.2

## ❤️ Unterstützung

Wenn dir die Integration hilft und du die Weiterentwicklung unterstützen möchtest, freue ich mich über eine Spende über die **Sponsoring-Sektion** dieses Repositories (Button "Sponsor" oben auf der [Projektseite](https://github.com/derolli1976/enpal)) oder über [Buy Me a Coffee](https://buymeacoffee.com/derolli1976). Danke!
