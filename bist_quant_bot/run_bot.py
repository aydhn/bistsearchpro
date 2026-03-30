import asyncio
from config.config_manager import ConfigManager
from core.live_engine import LiveEngine
from health_check import HealthCheck
import sys

"""
Ana Giriş Noktası (Entry Point).
Sistemi ayağa kaldıran yegane modül.
"""
if __name__ == "__main__":
    # Pre-Flight Check (Phase 24)
    checker = HealthCheck()
    try:
        checker.run_all()
    except SystemExit:
        print("Sağlık taraması başarısız. Bot başlatılamadı.")
        sys.exit(1)

    # Ayarları Yükle
    config = ConfigManager("config/config.json")

    # Motoru Çalıştır
    engine = LiveEngine(config)
    try:
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        print("Sistem admin tarafından manuel kapatıldı.")
