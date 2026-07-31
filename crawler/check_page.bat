@echo off
cd /d "%~dp0"
echo ============================================
echo  Naver Shopping page structure check
echo ============================================
echo.
set "PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if not defined PY python --version >nul 2>&1
if not defined PY if not errorlevel 1 set "PY=python"
if not defined PY echo [ERROR] Python is not installed, or not in PATH.
if defined PY %PY% check_page.py
echo.
pause
