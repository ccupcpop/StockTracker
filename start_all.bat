@echo off
chcp 65001 >nul 2>&1
title Taiwan Stock Analysis System

echo ========================================
echo   Taiwan Stock Analysis System
echo   Auto-refresh every 5 minutes
echo ========================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python installed
echo.

:: Start HTTP server in background
echo [1/2] Starting HTTP server on port 8000...
start "HTTP Server" cmd /c "python -m http.server 8000"

:: Wait 2 seconds then open browser
timeout /t 2 /nobreak >nul
start "" http://localhost:8000

:: Run stock analysis loop in this window
echo [2/2] Starting stock data collector...
echo.
echo ----------------------------------------
echo   HTTP Server: http://localhost:8000
echo   Data updates every 5 minutes
echo   Press Ctrl+C to stop
echo ----------------------------------------
echo.

python stock_loop.py

pause
