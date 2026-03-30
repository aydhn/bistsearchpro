#!/bin/bash
# Linux/WSL İçin Launcher Script
# Aynı mantıkla çalışan, arka planda çalıştırılabilecek Bash scripti.

echo "ED Capital BIST Bot - Linux Launcher"
VENV_DIR="venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Sanal ortam bulunamadı, oluşturuluyor..."
    python3 -m venv $VENV_DIR
    source $VENV_DIR/bin/activate
    echo "Bağımlılıklar yükleniyor..."
    pip install -r requirements.txt
else
    source $VENV_DIR/bin/activate
fi

while true; do
    echo "[$(date)] Sistem Başlatılıyor..."
    python live_engine.py

    # Hata kontrolü
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "Kritik Hata (Crash). Sistem 10 saniye içinde tekrar başlatılacak..."
        sleep 10
    else
        echo "Sistem normal kapandı."
        break
    fi
done
