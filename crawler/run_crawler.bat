@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================
echo  SLBS 캐릭터 마켓 레이더 - 수집기 실행
echo ============================================
pip install -r requirements.txt --quiet
python crawler.py
echo.
pause
