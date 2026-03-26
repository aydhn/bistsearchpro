@echo off
title BIST Quant Alpha - Algorithmic Trading Bot
echo ==========================================================
echo BIST Quant Alpha Baslatiliyor...
echo ==========================================================

REM Sanal ortami (virtual environment) aktif etme ornegi
REM Eger sanal ortam kullaniyorsaniz asagidaki satiri yorumdan cikarin:
REM call venv\Scripts\activate.bat

echo 1. Arka planda Ana Dongu (Sinyal Motoru) baslatiliyor...
REM run_bot.py asenkron olarak arka planda calistirilacak.
start /B python run_bot.py

echo 2. Streamlit Dashboard Komuta Merkezi baslatiliyor...
REM Streamlit dashboard local port (8501) uzerinden browser'i acacak.
streamlit run dashboard.py

echo ==========================================================
echo Sistem basariyla calisiyor.
echo Kapatmak icin bu pencereyi ve Streamlit penceresini (Ctrl+C) kapatiniz.
echo ==========================================================
pause
