# Deployment Script für Home Assistant Test-Installation
# Kopiert die Integration in die Home Assistant Installation

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Enpal Webparser - Deployment Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Pfad zur Home Assistant Installation
$haPath = Read-Host "Pfad zur Home Assistant Installation (z.B. C:\Users\<user>\AppData\Roaming\.homeassistant)"

if (-not (Test-Path $haPath)) {
    Write-Host "ERROR: Pfad existiert nicht: $haPath" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Home Assistant Pfad gefunden: $haPath" -ForegroundColor Green

# Ziel-Pfad
$targetPath = Join-Path $haPath "custom_components\enpal_webparser"
$sourcePath = "custom_components\enpal_webparser"

Write-Host ""
Write-Host "Quelle: $sourcePath" -ForegroundColor Yellow
Write-Host "Ziel:   $targetPath" -ForegroundColor Yellow
Write-Host ""

# Backup erstellen wenn Integration bereits existiert
if (Test-Path $targetPath) {
    $backupPath = "$targetPath.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Write-Host "⚠ Integration existiert bereits - Erstelle Backup..." -ForegroundColor Yellow
    Copy-Item -Path $targetPath -Destination $backupPath -Recurse
    Write-Host "✓ Backup erstellt: $backupPath" -ForegroundColor Green
    Write-Host ""
    
    # Alte Version löschen
    Remove-Item -Path $targetPath -Recurse -Force
    Write-Host "✓ Alte Version entfernt" -ForegroundColor Green
}

# Integration kopieren
Write-Host "📦 Kopiere Integration..." -ForegroundColor Cyan
Copy-Item -Path $sourcePath -Destination $targetPath -Recurse

Write-Host "✓ Integration kopiert" -ForegroundColor Green
Write-Host ""

# Prüfe ob wichtige Dateien vorhanden sind
Write-Host "🔍 Prüfe Dateien..." -ForegroundColor Cyan

$requiredFiles = @(
    "__init__.py",
    "config_flow.py",
    "sensor.py",
    "manifest.json",
    "const.py",
    "utils.py",
    "entity_factory.py",
    "wallbox_api.py",
    "button.py",
    "switch.py",
    "select.py",
    "discovery.py",
    "api\__init__.py",
    "api\base.py",
    "api\websocket_client.py",
    "api\websocket_parser.py",
    "api\html_client.py",
    "api\protocol.py"
)

$allPresent = $true
foreach ($file in $requiredFiles) {
    $filePath = Join-Path $targetPath $file
    if (Test-Path $filePath) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file FEHLT!" -ForegroundColor Red
        $allPresent = $false
    }
}

Write-Host ""

if (-not $allPresent) {
    Write-Host "❌ Einige Dateien fehlen! Bitte prüfen." -ForegroundColor Red
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ DEPLOYMENT ERFOLGREICH!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Nächste Schritte:" -ForegroundColor Yellow
Write-Host "  1. Home Assistant neu starten" -ForegroundColor White
Write-Host "  2. Logs prüfen auf Fehler" -ForegroundColor White
Write-Host "  3. Bestehende Integration sollte automatisch migrieren" -ForegroundColor White
Write-Host "  4. Oder neue Integration hinzufügen und Auto-Detection testen" -ForegroundColor White
Write-Host ""
Write-Host "Log-Kommandos:" -ForegroundColor Yellow
Write-Host '  Logs ansehen: Get-Content "$haPath\home-assistant.log" -Tail 100 -Wait' -ForegroundColor White
Write-Host '  Enpal-Logs:   Get-Content "$haPath\home-assistant.log" | Select-String -Pattern "\[Enpal\]"' -ForegroundColor White
Write-Host ""

# Optional: Home Assistant Service neu starten (wenn als Service installiert)
$restart = Read-Host "Home Assistant jetzt neu starten? (j/n)"
if ($restart -eq "j" -or $restart -eq "J") {
    Write-Host "🔄 Starte Home Assistant neu..." -ForegroundColor Cyan
    try {
        Restart-Service -Name "HomeAssistant" -ErrorAction Stop
        Write-Host "✓ Home Assistant wird neu gestartet" -ForegroundColor Green
    } catch {
        Write-Host "⚠ Konnte Service nicht automatisch neu starten." -ForegroundColor Yellow
        Write-Host "  Bitte manuell neu starten über Home Assistant UI oder:" -ForegroundColor White
        Write-Host "  Restart-Service -Name 'HomeAssistant'" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "Viel Erfolg beim Testing! 🚀" -ForegroundColor Cyan
