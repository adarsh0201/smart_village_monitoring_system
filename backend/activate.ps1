# Quick activator when inside backend directory
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

try {
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force -ErrorAction SilentlyContinue
} catch {}

$VenvScript = Join-Path $ScriptDir "venv\Scripts\Activate.ps1"

if (Test-Path $VenvScript) {
    . $VenvScript
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "✓ Smart Village Monitor Backend Virtual Environment Active" -ForegroundColor Green
    Write-Host "• Python:     $((Get-Command python).Source)" -ForegroundColor Gray
    Write-Host "• Working Dir: $(Get-Location)" -ForegroundColor Gray
    Write-Host "• You can now run: python manage.py runserver" -ForegroundColor Yellow
    Write-Host "==========================================================" -ForegroundColor Cyan
} else {
    Write-Host "✗ Virtual environment not found at venv" -ForegroundColor Red
}
