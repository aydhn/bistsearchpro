@echo off
echo ===========================================
echo  ED CAPITAL - WINDOWS LAUNCHER (Phase 14)
echo ===========================================

REM Sanal ortam aktivasyonu (Eger varsa)
REM call venv\Scripts\activate

:RESTART
echo [%time%] Bot baslatiliyor...
python ../run_bot.py

echo.
echo [%time%] Sistem bir hata nedeniyle kapandi (Crash).
echo Watchdog Devrede: 10 Saniye icinde yeniden baslatilacak...
timeout /t 10 /nobreak > NUL
goto RESTART
