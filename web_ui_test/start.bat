@echo off
cd /d "%~dp0"

echo ========================================
echo   AI Auto Renovation - Local Server
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found, please install Python 3
    echo.
    echo Download: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [INFO] Python is installed
echo [INFO] Starting server...
echo.
echo   Visit: http://localhost:13100/main.html
echo.
echo   Press Ctrl+C to stop server
echo ========================================
echo.

REM Start HTTP server
python -m http.server 13100

REM If server exits abnormally, show error
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server failed to start, error code: %errorlevel%
    echo.
    pause
)
