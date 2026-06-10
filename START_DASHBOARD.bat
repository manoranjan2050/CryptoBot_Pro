@echo off
title CryptoBot Pro - Setup and Launch
color 0B
cls

echo.
echo  =====================================================
echo    B  CryptoBot Pro - Auto Setup and Launch
echo  =====================================================
echo.

:: ── Check for Python ──────────────────────────────────
echo  [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [!] Python not found. Opening download page...
    echo      Please install Python 3.10+ then re-run this file.
    echo      Make sure to check "Add Python to PATH" during install!
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [OK] Python %PYVER% found

:: ── Check for Node.js ─────────────────────────────────
echo  [2/5] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [!] Node.js not found. Opening download page...
    echo      Please install Node.js LTS then re-run this file.
    echo.
    start https://nodejs.org/en/download
    pause
    exit /b
)
for /f %%v in ('node --version 2^>^&1') do set NODEVER=%%v
echo  [OK] Node.js %NODEVER% found

:: ── Install Python dependencies ───────────────────────
echo  [3/5] Installing Python packages...
cd /d "%~dp0backend"
pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo  [!] Failed to install Python packages. Trying with --user flag...
    pip install -r requirements.txt --user --quiet --disable-pip-version-check
)
echo  [OK] Python packages ready

:: ── Install Node dependencies ─────────────────────────
echo  [4/5] Installing frontend packages (first time may take a minute)...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    call npm install --silent
    if errorlevel 1 (
        echo  [!] npm install failed. Trying without silent mode...
        call npm install
    )
) else (
    echo  [OK] node_modules already exists, skipping install
)
echo  [OK] Frontend packages ready

:: ── Launch both servers ───────────────────────────────
echo  [5/5] Launching servers...
echo.

:: Start backend in new window
start "CryptoBot Backend" cmd /k "color 0A && title CryptoBot Backend (Port 8000) && cd /d "%~dp0backend" && echo  Starting FastAPI backend... && python main.py"

:: Wait 3 seconds for backend to start
timeout /t 3 /nobreak >nul

:: Start frontend in new window
start "CryptoBot Frontend" cmd /k "color 0B && title CryptoBot Frontend (Port 3000) && cd /d "%~dp0frontend" && echo  Starting React frontend... && npm run dev"

:: Wait for frontend to compile
timeout /t 5 /nobreak >nul

:: Open browser
echo  Opening dashboard in browser...
start http://localhost:3000

echo.
echo  =====================================================
echo   Dashboard is running!
echo.
echo   URL    : http://localhost:3000
echo   Login  : demo / demo123
echo.
echo   Two windows opened:
echo     - CryptoBot Backend  (port 8000)
echo     - CryptoBot Frontend (port 3000)
echo.
echo   Close those two windows to stop the servers.
echo  =====================================================
echo.
pause
