# Mitwirken an der Enpal Solar Integration

Danke, dass du zu diesem Projekt beitragen möchtest. Beiträge sind willkommen,
egal ob Fehlerbericht, Verbesserungsvorschlag, Dokumentation oder Code.

## Bevor du startest

- Lies den [Verhaltenskodex](CODE_OF_CONDUCT.md). Mit deiner Teilnahme stimmst du ihm zu.
- Schau in die [bestehenden Issues](https://github.com/derolli1976/enpal/issues),
  ob dein Thema schon bekannt ist.
- Die Integration richtet sich an Enpal-Boxen mit lokaler Weboberfläche. Nicht
  jede Enpal-Anlage wird unterstützt.

## Fehler melden

Nutze die [Bug-Report-Vorlage](https://github.com/derolli1976/enpal/issues/new/choose)
und gib bitte an:

- Verwendete Version der Integration und Home Assistant
- Firmware-Stand der Enpal Box
- Genutzter Modus (WebSocket oder HTML)
- Relevante Log-Ausgaben (Zeilen mit dem Präfix `[Enpal]`)
- Schritte zum Reproduzieren

## Funktionen vorschlagen

Nutze die [Feature-Request-Vorlage](https://github.com/derolli1976/enpal/issues/new/choose).
Beschreibe das Problem, das du lösen möchtest, und nicht nur die gewünschte Lösung.

## Entwicklungsumgebung einrichten

```bash
# Virtuelle Umgebung anlegen und aktivieren
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell

# Abhängigkeiten installieren
pip install -r requirements.txt
```

## Tests ausführen

Die Tests setzen `PYTHONPATH` auf das Projekt-Root voraus.

```bash
# Windows PowerShell
$env:PYTHONPATH = "e:\Github\enpal"

# Alle Tests
pytest

# Einzelne Testdatei
pytest custom_components/enpal_webparser/tests/test_utils.py

# Mit ausführlicher Ausgabe
pytest -v
```

Neue oder geänderte Funktionen sollten durch Tests abgedeckt sein. Die Tests
nutzen echte HTML-Fixtures aus `custom_components/enpal_webparser/tests/fixtures/`.

## Code-Konventionen

- Alle Log-Ausgaben beginnen mit dem Präfix `[Enpal]`, zum Beispiel
  `_LOGGER.info("[Enpal] Nachricht: %s", wert)`.
- Sensor-Logik liegt in `utils.py`, Konstanten in `const.py`.
- Halte dich an den vorhandenen Stil und füge keine Funktionen hinzu, die über
  den Zweck deiner Änderung hinausgehen.

## Pull Requests

1. Erstelle einen Branch für deine Änderung (z. B. `fix/...` oder `feature/...`).
2. Halte den Pull Request klein und auf ein Thema fokussiert.
3. Fülle die [Pull-Request-Vorlage](.github/pull_request_template.md) aus.
4. Stelle sicher, dass alle Tests erfolgreich durchlaufen.
5. Aktualisiere die Dokumentation, wenn sich das Verhalten ändert.

## Lizenz

Mit dem Einreichen eines Beitrags stimmst du zu, dass dein Beitrag unter der
[MIT-Lizenz](LICENSE) des Projekts veröffentlicht wird.
