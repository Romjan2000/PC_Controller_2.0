@echo off
title PC Controller Setup
color 0A
echo.
echo  ====================================
echo   PC CONTROLLER - SETUP WIZARD
echo  ====================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)
echo [OK] Python found

:: Create virtual environment
if not exist "venv" (
    echo [*] Creating virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment exists
)

:: Activate and install dependencies
echo [*] Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
echo [OK] Dependencies installed

:: Create .env from example if needed
if not exist ".env" (
    if exist ".env.example" (
        echo [*] Creating .env from template...
        copy .env.example .env >nul
        echo [OK] .env file created
        echo.
        echo  ====================================
        echo   IMPORTANT: Edit .env file!
        echo  ====================================
        echo.
        echo Please edit the .env file with your settings:
        echo  - Set a secure password for APP_PASSWORD_PLAIN
        echo  - Optional: Add Telegram bot token for notifications
        echo.
        notepad .env
    )
) else (
    echo [OK] .env file exists
)

:: Check for Cloudflare
if not exist "cloudflared.exe" (
    echo.
    echo  ====================================
    echo   CLOUDFLARE TUNNEL (Recommended)
    echo  ====================================
    echo.
    echo To enable remote access, download cloudflared.exe:
    echo https://github.com/cloudflare/cloudflared/releases/latest
    echo.
    echo Download 'cloudflared-windows-amd64.exe' and rename to 'cloudflared.exe'
    echo Place it in this folder: %CD%
    echo.
) else (
    echo [OK] Cloudflared found
)

echo.
echo  ====================================
echo   SETUP COMPLETE!
echo  ====================================
echo.
echo Run 'run.bat' to start PC Controller
echo.
pause
