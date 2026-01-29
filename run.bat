@echo off
title PC Controller
color 0B

:: Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [!] Virtual environment not found. Run setup.bat first!
    pause
    exit /b 1
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
echo.

:: Run the controller
pythonw Controller.pyw
