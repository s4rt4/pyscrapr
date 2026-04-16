@echo off
title PyScrapr Launcher
cd /d "%~dp0"

echo ========================================
echo   PyScrapr - Web Scraping Toolkit
echo ========================================
echo.
echo Starting backend (FastAPI)  - http://localhost:8000
echo Starting frontend (Vite)    - http://localhost:5173
echo.

REM Start backend in a new window
start "PyScrapr Backend" cmd /k "cd /d %~dp0backend && python run.py"

REM Start frontend in a new window
start "PyScrapr Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

REM Wait for frontend to be ready, then open browser
start "PyScrapr Browser" /min cmd /c "timeout /t 4 /nobreak >nul && start """" http://localhost:5173"

echo.
echo Both servers are starting in separate windows.
echo Close this window or press any key to dismiss.
pause >nul
