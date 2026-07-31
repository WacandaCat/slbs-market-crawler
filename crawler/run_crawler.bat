@echo off
cd /d "%~dp0"
echo ============================================
echo  SLBS Character Market Radar - Crawler
echo ============================================
echo.
set "PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if not defined PY python --version >nul 2>&1
if not defined PY if not errorlevel 1 set "PY=python"
if not defined PY echo [ERROR] Python is not installed, or not in PATH.
if not defined PY echo.
if not defined PY echo   1. Open https://www.python.org/downloads/
if not defined PY echo   2. Download the Windows installer and run it
if not defined PY echo   3. On the FIRST screen, check "Add python.exe to PATH"
if not defined PY echo   4. Finish the install, close this window, run this file again
if defined PY echo Installing required packages...
if defined PY %PY% -m pip install -r requirements.txt --quiet
if defined PY echo.
if defined PY %PY% crawler.py
echo.
pause
