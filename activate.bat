@echo off
rem Quick activator for Smart Village Monitor backend virtual environment
set "SCRIPT_DIR=%~dp0"
set "ACTIVATE_BAT=%SCRIPT_DIR%backend\venv\Scripts\activate.bat"

if exist "%ACTIVATE_BAT%" (
    call "%ACTIVATE_BAT%"
    cd /d "%SCRIPT_DIR%backend"
    echo ==========================================================
    echo [✓] Backend Virtual Environment Activated
    echo [•] Working Directory: %CD%
    echo [•] You can now run: python manage.py ^<command^>
    echo ==========================================================
) else (
    echo [!] Virtual environment not found at %SCRIPT_DIR%backend\venv
)
