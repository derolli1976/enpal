# 3.1.1 - Reparatur-Meldung bei festem HTML-Modus auf Firmware 8.51

Kleines Folge-Release zu 3.1.0. Es schließt eine Lücke für Installationen, die fest auf den HTML-Modus konfiguriert sind.

---

## 🐛 Behobene Fehler

### Alle Entitäten "nicht verfügbar" nach Firmware-Update auf 8.51 im HTML-Modus

Steht die Datenquelle in den Optionen fest auf "HTML" und Enpal aktualisiert die Box auf Firmware **Solar Rel. 8.51**, liefert die Seite `/deviceMessages` nur noch die Karte "Site Data". Fast alle Entitäten standen dann dauerhaft auf "nicht verfügbar", ohne Hinweis auf die Ursache.

Die Integration erkennt diese Situation jetzt selbst: Sie liest bei jedem Abruf die Firmware-Version der Box mit. Meldet die Box Firmware 8.51 oder neuer, während der HTML-Modus aktiv ist, erscheint unter **Einstellungen → Reparaturen** eine Meldung. Ein Klick auf "Senden" stellt die Datenquelle auf den WebSocket-Modus um. Die Integration startet danach automatisch neu und alle Sensoren sind wieder da.

Wird die Firmware-Version nicht erkannt oder läuft die Box auf 8.50 oder älter, ändert sich nichts. Der HTML-Modus bleibt für ältere Firmware voll unterstützt.

## 🔄 Kompatibilität

- Keine Änderungen an Entity-IDs, Sensoren oder Optionen
- Die Umstellung auf WebSocket erfolgt nur nach Bestätigung durch dich, nie automatisch

## ❤️ Unterstützung

Wenn dir die Integration hilft und du die Weiterentwicklung unterstützen möchtest, freue ich mich über eine Spende über die **Sponsoring-Sektion** dieses Repositories (Button "Sponsor" oben auf der [Projektseite](https://github.com/derolli1976/enpal)) oder über [Buy Me a Coffee](https://buymeacoffee.com/derolli1976). Danke!
