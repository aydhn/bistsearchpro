import json
import os
import sqlite3
import urllib.request
from config.config_manager import ConfigManager
from core.logger_engine import LoggerEngine

# "Pre-Flight Check" mantığı "Silent Failure" (Sessizce Çökme ve Yanlış İşlem Yapma)
# riskini sıfıra indirir. Eksik bir ortamda çalışan kurumsal bir fon botu, faciaya yol açar.

logger = LoggerEngine.get_system_logger()

class HealthCheck:
    @staticmethod
    def run_all():
        logger.info("Ön Uçuş Kontrolü (Pre-Flight Check) başlatıldı.")

        try:
            HealthCheck._test_config()
            HealthCheck._test_database_io()
            HealthCheck._test_network()

            logger.info("Ön Uçuş Kontrolleri Tamamlandı. Sistem %100 sağlıklı.")
            return True
        except Exception as e:
            logger.error(f"Kritik Hata (Pre-Flight Fail): {e}")
            print(f"\033[91mCRITICAL ERROR: {e}\033[0m")
            return False

    @staticmethod
    def _test_config():
        logger.info("Test 1: Konfigürasyon dosyası kontrolü...")
        config_path = "config/config.json"
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"{config_path} eksik.")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError:
            raise ValueError(f"{config_path} formatı bozuk.")

        # Parametrelerin mevcut ve tip doğruluğunu Test ediyoruz.
        ConfigManager()

    @staticmethod
    def _test_database_io():
        logger.info("Test 2: Veritabanı I/O izinleri kontrolü...")
        db_path = "data/portfolio.db"
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS _health_check (id INTEGER)")
            cursor.execute("INSERT INTO _health_check VALUES (1)")
            conn.commit()
            cursor.execute("DROP TABLE _health_check")
            conn.commit()
            conn.close()
        except Exception as e:
            raise PermissionError(f"Veritabanına yazma/okuma (I/O) izni yok. Detay: {e}")

    @staticmethod
    def _test_network():
        logger.info("Test 3: Ağ ve API bağlantı kontrolü...")
        telegram_token = ConfigManager.get("api_keys", "TELEGRAM_TOKEN")
        if telegram_token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
            raise ValueError("TELEGRAM_TOKEN yapılandırılmamış.")

        try:
            # Telegram API Ping
            req = urllib.request.Request(f"https://api.telegram.org/bot{telegram_token}/getMe")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status != 200:
                    raise ConnectionError("Telegram API erişimi reddedildi.")
        except Exception as e:
            raise ConnectionError(f"Telegram API'sine ulaşılamadı. İnternet bağlantınızı kontrol edin: {e}")
