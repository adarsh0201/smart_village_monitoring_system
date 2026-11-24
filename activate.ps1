# PowerShell Activation Script for Smart Village Monitor Root
param()

$ErrorActionPreference = "SilentlyContinue"
try {
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force -ErrorAction SilentlyContinue
} catch {}

$BackendDir = Join-Path $PSScriptRoot "backend"
$VenvScript = Join-Path $BackendDir "venv\Scripts\Activate.ps1"

if (Test-Path $VenvScript) {
    Set-Location $BackendDir
    . $VenvScript
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "[SUCCESS] Smart Village Backend Environment Activated!" -ForegroundColor Green
    Write-Host "Working Directory: $(Get-Location)" -ForegroundColor Cyan
    Write-Host "Python Path:       $((Get-Command python).Source)" -ForegroundColor Cyan
    Write-Host "Run Server:        python manage.py runserver" -ForegroundColor Yellow
    Write-Host "==========================================================" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Virtual environment not found at: $VenvScript" -ForegroundColor Red
}
