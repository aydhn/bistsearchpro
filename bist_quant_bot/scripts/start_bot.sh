#!/bin/bash
echo "==========================================="
echo " ED CAPITAL - LINUX/WSL LAUNCHER (Phase 14)"
echo "==========================================="

# Sanal ortam aktivasyonu (Eger varsa)
# source venv/bin/activate

while true; do
    echo "[$(date)] Bot baslatiliyor..."
    python3 ../run_bot.py

    echo "[$(date)] Sistem bir hata nedeniyle kapandi (Crash)."
    echo "Watchdog Devrede: 10 Saniye icinde yeniden baslatilacak..."
    sleep 10
done
