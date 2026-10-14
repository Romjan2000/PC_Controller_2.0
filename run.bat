@echo off
title PC Controller
color 0B

:: Check and auto-create virtual environment if missing
if not exist "venv\Scripts\activate.bat" (
    echo [*] First-time launch detected! Setting up environment...
    echo [*] Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [*] Installing dependencies from requirements.txt...
    pip install -r requirements.txt --quiet
    if not exist ".env" (
        if exist ".env.example" (
            copy .env.example .env >nul
            echo [OK] Default .env created from template.
        )
    )
    echo [OK] Environment setup complete!
) else (
    call venv\Scripts\activate.bat
)

:: Check .env
if not exist ".env" (
    echo [!] .env file not found. Run setup.bat first!
    pause
    exit /b 1
)

echo.
echo  ================================
echo   PC CONTROLLER - Starting...
echo  ================================
echo.
echo Press Ctrl+C to stop the server
echo (For completely silent background mode, run silent_start.vbs)
echo.

:: Run the controller with console output
python Controller.pyw
