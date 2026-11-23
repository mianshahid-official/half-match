@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo   Match the Halves - Kids Video Generator
echo ===================================================
echo.

:: Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not found on your system PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    echo and ensure "Add Python to PATH" is checked during installation.
    echo.
    pause
    exit /b 1
)

:: Launch the PySide6 Desktop GUI application
echo Starting application...
python main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Application exited with an error code: %ERRORLEVEL%
    pause
)
