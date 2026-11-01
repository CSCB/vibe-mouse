@echo off
setlocal EnableExtensions
title Vibe Mouse
chcp 65001 >nul 2>&1
cd /d "%~dp0"

rem Pick an usable Python: prefer project .venv, fall back to system python.
set "PY="
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys" >nul 2>&1 && set "PY=.venv\Scripts\python.exe"
)
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [ERROR] No usable Python found.
    echo         Install Python 3.9+ first, or run install.bat to set up the environment.
    pause
    exit /b 1
)

echo [Vibe Mouse] Starting with interpreter: %PY%
echo [Vibe Mouse] Usage: start.bat [--gui]
echo.

"%PY%" -m core.main %*
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" (
    echo.
    echo [Vibe Mouse] Exited with code %CODE%.
    pause
)

endlocal
