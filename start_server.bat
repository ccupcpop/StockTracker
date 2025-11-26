@echo off
chcp 65001 >nul 2>&1
title Stock Analysis Server

echo ========================================
echo   Taiwan Stock Analysis System
echo   Starting Local Server...
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
echo Starting server at http://localhost:8000
echo Do not close this window
echo.
echo ----------------------------------------

start "" http://localhost:8000

python -m http.server 8000

pause
