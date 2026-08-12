# 3.1.0 - Unterstützung für Firmware 8.51

Enpal hat mit **Solar Rel. 8.51** die lokale Datenseite der Box grundlegend umgebaut. Auf Anlagen mit dieser Firmware standen seitdem fast alle Entitäten auf "nicht verfügbar". Diese Version stellt die volle Funktion wieder her und macht die Integration robuster gegen künftige Umbauten durch Enpal.

Dieses Release bündelt die Ergebnisse der Beta-Reihe 3.0.3b1 bis b13. Getestet gegen Huawei-Anlagen mit Firmware 8.50 und 8.51 sowie eine FoxESS-Anlage mit 8.51.

---

## 🐛 Behobene Fehler

### Alle Entitäten "nicht verfügbar" unter Firmware 8.51

Unter 8.51 liefert die HTTP-Seite `/deviceMessages` nur noch die Karte "Site Data". Alle Gerätetabellen schickt die Box stattdessen kurz nach dem Verbindungsaufbau als großes Datenpaket über den WebSocket. Die Integration hat dieses Paket bisher verworfen und nur die kleinen Änderungs-Diffs ausgewertet. Sensoren tauchten deshalb erst auf, wenn sich ihr Wert zufällig änderte; selten aktualisierte Sensoren blieben dauerhaft "nicht verfügbar".

Die Integration liest das Initial-Paket jetzt vollständig aus. Alle Sensoren sind direkt nach dem Start wieder da. Die Zeilenerkennung arbeitet dabei mit dem Namensmuster der Sensor-Keys statt mit festen Listen und funktioniert damit auf allen Anlagentypen.

### Ausgeblendete Werte (SOC, Batterietemperatur, Batteriespannung)

Firmware 8.51 verbirgt einen Teil der Werte hinter den Checkboxen "Show unsupported values" und "Show internal values". Die Integration schaltet diese Checkboxen jetzt auf ihrer eigenen Verbindung ein. Die Ursache der in den Betas b7 bis b10 fehlgeschlagenen Klicks war ein einzelnes überzähliges Feld in der Klick-Nachricht, das die Box ablehnt. Nach der Korrektur akzeptiert die Box jeden Klick.

### Sensoren zeigen Fehlertexte statt Werte

Firmware 8.51 ergänzt eine Spalte "Notes". Zeilen ohne gültigen Messwert enthalten nur noch eine Notiz wie `missing: The value has been cleared.` Der Parser hat diese Notiz als Messwert gelesen. Solche Zeilen werden jetzt übersprungen; der Sensor behält seinen letzten bekannten Wert.

### Umbenannte Sensor-Keys behalten ihre Entity-IDs

Firmware 8.51 hat mehrere Datenpunkte um Suffixe wie `.Inverter` erweitert. Diese Keys werden auf ihre bisherigen Namen zurückgeführt, damit Automatisierungen und Verlaufsdaten weiterlaufen.

### Inverter-Systemstatus wird wieder zerlegt

Die Box liefert `Inverter.System.State` unter 8.51 als HTML-Liste mit über 800 Zeichen. Die Integration entfernt die HTML-Auszeichnung und zerlegt den Wert wie bisher in die bekannten Teilsensoren (`sensor.inverter_system_state_decimal`, `_flags` und die einzelnen Statusbits) mit unveränderten Entity-IDs.

## ✨ Neue Funktionen

### Gruppenauswahl blendet nur noch aus, statt zu filtern

Bisher hat die Integration abgewählte Gerätegruppen komplett ignoriert. Verschob Enpal Sensoren in eine andere Gruppe oder kam eine neue Gruppe hinzu, fehlten die Werte, bis man die Optionen anpasste.

Ab dieser Version werden immer alle Gruppen gelesen. Die Auswahl in den Optionen bestimmt nur noch, ob die Entities einer Gruppe in Home Assistant standardmäßig aktiviert sind. Abgewählte Gruppen erzeugen deaktivierte Entities, die sich jederzeit einzeln einschalten lassen. Neue Gruppen, die es zum Zeitpunkt deiner Konfiguration noch nicht gab, sind automatisch aktiv. Bestehende Konfigurationen werden automatisch übernommen.

### Neue Gerätegruppe "ControlBox"

Neuere Anlagen (z. B. mit FoxESS-Wechselrichter und Starcharge-Wallbox) haben eine zusätzliche Karte "ControlBox" mit EEBUS- und Smart-Meter-Gateway-Werten. Die Gruppe ist jetzt bekannt und bei bestehenden Installationen automatisch aktiv.

### Unbekannte Sensoren landen unter "Uncategorized"

Sensor-Keys, die die Integration keiner Gruppe zuordnen kann (z. B. nach künftigen Firmware-Updates), werden unter der Gruppe "Uncategorized" angelegt statt verworfen. Der Wert ist damit sofort verfügbar.

### Über 115 neue Sensor-Zuordnungen

Die Tabelle, die Sensor-Keys ihren Gerätegruppen zuordnet, wurde um die Werte einer FoxESS-Anlage mit Firmware 8.51 und um belegte Huawei-Keys aus 8.50-Aufzeichnungen erweitert. Historische Keys nutzen ihre bisherigen Gruppen, damit die alten Entity-IDs weiterverwendet werden.

## 🔄 Kompatibilität

- **Firmware 8.51**: voll unterstützt (Huawei und FoxESS, live getestet)
- **Firmware 8.50**: unverändert unterstützt, per Aufzeichnungs-Replay und Live-Test verifiziert
- **Ältere Firmware (HTML-Modus)**: unverändert
- Entity-IDs bleiben stabil; bestehende Automatisierungen, Dashboards und Verlaufsdaten laufen weiter

## 📋 Bekannte Einschränkungen

- Wenige Keys stehen auf der Seite in zwei Karten gleichzeitig (z. B. `Setting.Charge.From.Grid`, `SoftwareVersion.Service.2.Fox`). Sie erscheinen als einzelner "Uncategorized"-Sensor.
- Wird ein "Uncategorized"-Key in einer späteren Version einer richtigen Gruppe zugeordnet, entsteht eine neue Entity-ID.
- Zeilen ohne Messwert (Notiz "invalid" oder "missing") werden übersprungen. Der Sensor behält seinen letzten bekannten Wert.

## 🙏 Danksagung

Diese Version ist das Ergebnis von zwei Wochen gemeinsamer Fehlersuche in [Issue #148](https://github.com/derolli1976/enpal/issues/148).

Ein besonderer Dank gilt **@Ghostryder81**. Er hat einen VPN-Zugang zu seiner Enpal-Box bereitgestellt. Erst dadurch konnten wir das Klick-Protokoll der Box im Vergleich mit einem echten Browser analysieren, die Ursache der fehlgeschlagenen Checkbox-Klicks finden und jede Änderung live verifizieren. Ohne diesen Zugang wäre dieses Release nicht möglich gewesen.

Danke außerdem an:

- **@Graib** für die vielen Sniffer-Läufe, Debug-Logs und die präzisen Testberichte über die gesamte Beta-Reihe
- **@vito86b** fürs Melden des Problems und die ersten Rohdaten der Firmware 8.51
- **@Didoo74** für die Analyse der Data-Collector-Seite als alternative Datenquelle
- **@Araknus13** für die Entdeckung, dass die fehlenden Werte nur hinter Checkboxen versteckt sind, samt funktionierendem Playwright-Nachweis

## ❤️ Unterstützung

Die Analyse und Behebung solcher Firmware-Umbauten kostet viele Abende. Wenn dir die Integration hilft und du die Weiterentwicklung unterstützen möchtest, freue ich mich über eine Spende über die **Sponsoring-Sektion** dieses Repositories (Button "Sponsor" oben auf der [Projektseite](https://github.com/derolli1976/enpal)) oder über [Buy Me a Coffee](https://buymeacoffee.com/derolli1976). Danke!
