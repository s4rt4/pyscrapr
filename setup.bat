@echo off
setlocal EnableDelayedExpansion
title PyScrapr Setup
cd /d "%~dp0"

echo ========================================
echo   PyScrapr - First-time Setup
echo ========================================
echo.
echo This script will:
echo   1. Detect Python 3.10+ and npm
echo   2. Install backend dependencies (pip)
echo   3. Install frontend dependencies (npm)
echo   4. Optional: install Playwright Chromium (~300 MB)
echo   5. Optional: create Desktop shortcut
echo.
pause

REM ---- Locate Python ----
echo.
echo [1/5] Detecting Python...
set PYTHON=
set CAND=C:\laragon\bin\python\python-3.10\python.exe
if exist "!CAND!" set PYTHON=!CAND!

if not defined PYTHON (
    python --version >nul 2>&1
    if not errorlevel 1 set PYTHON=python
)

if not defined PYTHON (
    py -3.10 --version >nul 2>&1
    if not errorlevel 1 set PYTHON=py -3.10
)

if not defined PYTHON (
    py -3.11 --version >nul 2>&1
    if not errorlevel 1 set PYTHON=py -3.11
)

if not defined PYTHON (
    py -3.12 --version >nul 2>&1
    if not errorlevel 1 set PYTHON=py -3.12
)

if not defined PYTHON (
    echo [ERROR] Python 3.10+ not found. Install from https://python.org
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('%PYTHON% --version 2^>^&1') do echo   Found: %%i ^(%PYTHON%^)

REM ---- Locate npm ----
echo.
echo [2/5] Detecting npm...
where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm not found. Install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo   Found: Node %%i

REM ---- Backend deps ----
echo.
echo [3/5] Installing backend dependencies (this may take 5-10 minutes)...
echo   Includes: fastapi, uvicorn, sqlalchemy, torch, open-clip-torch, playwright, yt-dlp, etc.
echo.
%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install -r backend\requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Backend dependency install failed. Check the error above.
    pause
    exit /b 1
)
echo   Backend dependencies OK.

REM ---- Frontend deps ----
echo.
echo [4/5] Installing frontend dependencies...
cd frontend
call npm install
if errorlevel 1 (
    echo.
    echo [ERROR] npm install failed.
    cd ..
    pause
    exit /b 1
)
cd ..
echo   Frontend dependencies OK.

REM ---- Optional: Playwright chromium ----
echo.
echo [5/5] Optional: Playwright headless Chromium (~300 MB)
echo        Needed only if you want to use "Render dengan browser" toggle for JS-heavy sites.
set /p INSTALL_PW="Install Playwright Chromium now? [y/N]: "
if /i "%INSTALL_PW%"=="y" (
    %PYTHON% -m playwright install chromium
    if errorlevel 1 (
        echo   [WARN] Playwright install failed. You can retry later with:
        echo           %PYTHON% -m playwright install chromium
    ) else (
        echo   Playwright Chromium OK.
    )
) else (
    echo   Skipped. Run later with: %PYTHON% -m playwright install chromium
)

REM ---- Optional: Desktop shortcut ----
echo.
set /p MAKE_LNK="Create Desktop shortcut for PyScrapr launcher? [y/N]: "
if /i "%MAKE_LNK%"=="y" (
    powershell -ExecutionPolicy Bypass -File "%~dp0create-shortcut.ps1"
) else (
    echo   Skipped. You can create it later with: powershell -File create-shortcut.ps1
)

echo.
echo ========================================
echo   Setup complete!
echo ========================================
echo.
echo Next steps:
echo   - Double-click run-pyscrapr.bat (or the Desktop shortcut) to start
echo   - Backend will run on  http://localhost:8585
echo   - Frontend UI will open at  http://localhost:5173
echo   - Optional: install Ollama from https://ollama.com for AI Extract
echo.
pause
