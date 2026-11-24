# PowerShell Activation Script for Smart Village Monitor Backend
param()

$ErrorActionPreference = "SilentlyContinue"
try {
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force -ErrorAction SilentlyContinue
} catch {}

$VenvScript = Join-Path $PSScriptRoot "venv\Scripts\Activate.ps1"

if (Test-Path $VenvScript) {
    . $VenvScript
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "[SUCCESS] Smart Village Backend Environment Activated!" -ForegroundColor Green
    Write-Host "Python Path: $((Get-Command python).Source)" -ForegroundColor Cyan
    Write-Host "Run Server:  python manage.py runserver" -ForegroundColor Yellow
    Write-Host "==========================================================" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Virtual environment not found at: $VenvScript" -ForegroundColor Red
}
