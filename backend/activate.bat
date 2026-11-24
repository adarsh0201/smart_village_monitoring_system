@echo off
set "SCRIPT_DIR=%~dp0"
set "ACTIVATE_BAT=%SCRIPT_DIR%venv\Scripts\activate.bat"

if exist "%ACTIVATE_BAT%" (
    call "%ACTIVATE_BAT%"
    echo ==========================================================
    echo [✓] Backend Virtual Environment Activated
    echo [•] Working Directory: %CD%
    echo [•] You can now run: python manage.py runserver
    echo ==========================================================
) else (
    echo [!] Virtual environment not found at %SCRIPT_DIR%venv
)
