# Quick activator for Smart Village Monitor backend virtual environment
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Ensure script execution policy allows activating venv in current process
try {
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force -ErrorAction SilentlyContinue
} catch {}

$VenvScript = Join-Path $ScriptDir "backend\venv\Scripts\Activate.ps1"

if (Test-Path $VenvScript) {
    . $VenvScript
    Set-Location -Path (Join-Path $ScriptDir "backend")
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "✓ Smart Village Monitor Backend Virtual Environment Active" -ForegroundColor Green
    Write-Host "• Python:     $((Get-Command python).Source)" -ForegroundColor Gray
    Write-Host "• Working Dir: $(Get-Location)" -ForegroundColor Gray
    Write-Host "• You can now run: python manage.py <command>" -ForegroundColor Yellow
    Write-Host "==========================================================" -ForegroundColor Cyan
} else {
    Write-Host "✗ Virtual environment not found at backend\venv" -ForegroundColor Red
}
