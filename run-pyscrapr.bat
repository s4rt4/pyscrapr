@echo off
title PyScrapr Launcher
cd /d "%~dp0"

echo ========================================
echo   PyScrapr - Web Scraping Toolkit
echo ========================================
echo.

REM ---- Locate a Python that has uvicorn installed ----
REM User may have multiple Pythons (e.g. Laragon 3.10 + system 3.14).
REM We need the one where backend deps were actually installed.
set PYTHON=
call :try_python python
if not defined PYTHON call :try_python "py -3.10"
if not defined PYTHON call :try_python "py -3.11"
if not defined PYTHON call :try_python "py -3.12"
if not defined PYTHON call :try_python "py -3.13"
if not defined PYTHON call :try_python "py"
if not defined PYTHON call :try_python "C:\laragon\bin\python\python-3.10\python.exe"
goto after_python_detect

:try_python
%~1 -c "import uvicorn" >nul 2>nul
if not errorlevel 1 set PYTHON=%~1
exit /b 0

:after_python_detect
if not defined PYTHON (
    echo [ERROR] No Python installation with 'uvicorn' found.
    echo         Install backend dependencies first:
    echo           pip install -r backend\requirements.txt
    echo         Or activate your venv before running this launcher.
    echo.
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm not found in PATH.
    echo         Install Node.js 18+ from https://nodejs.org/
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%PYTHON% --version 2^>^&1') do set PYVER=%%i
for /f "tokens=*" %%i in ('node --version 2^>^&1') do set NODEVER=%%i
echo   Python  : %PYVER%  (%PYTHON%)
echo   Node    : %NODEVER%
echo   Project : %~dp0
echo.
echo Starting backend (FastAPI)  - http://localhost:8000
echo Starting frontend (Vite)    - http://localhost:5173
echo.

REM ---- Launch backend in new window ----
REM Use python -u for unbuffered output so errors show immediately.
REM Wrap in an error trap so window stays open if python crashes.
start "PyScrapr Backend" cmd /k "cd /d %~dp0backend && %PYTHON% -u run.py || (echo. & echo [BACKEND CRASHED] see error above & pause)"

REM ---- Launch frontend in new window ----
start "PyScrapr Frontend" cmd /k "cd /d %~dp0frontend && npm run dev || (echo. & echo [FRONTEND CRASHED] see error above & pause)"

REM ---- Wait for backend to actually respond, then open browser ----
echo Waiting for backend to be ready...
set /a TRIES=0
:waitloop
set /a TRIES+=1
if %TRIES% GTR 30 (
    echo.
    echo [WARN] Backend did not respond within 30 seconds.
    echo        Check the "PyScrapr Backend" window for errors.
    echo        Opening browser anyway in case frontend is up.
    goto openbrowser
)
timeout /t 1 /nobreak >nul
curl -s -o nul -w "" http://127.0.0.1:8000/api/docs/tree >nul 2>nul
if errorlevel 1 goto waitloop
echo   Backend ready after %TRIES% seconds.

:openbrowser
start "" http://localhost:5173

echo.
echo Both servers are running in separate windows.
echo Close those windows to stop the servers.
echo Close this window or press any key to dismiss.
pause >nul
