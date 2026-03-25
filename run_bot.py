import os
import sys
import asyncio
import logging
from config.settings import config
from core.state_manager import StateManager
from data.db_manager import DatabaseManager
from telegram_bot.notifier import TelegramNotifier
from core.paper_trader import PaperTrader
from telegram_bot.bot_commands import TelegramBotManager
from main_scheduler import MainScheduler

logger = logging.getLogger(__name__)

# --- Sistem Başlatıcı ve Kontrol ---
def verify_environment():
    """Gerekli tüm klasör yapısının varlığını işletim sistemi seviyesinde kontrol et."""
    directories = ["data", "logs", "config", "core", "strategies", "telegram", "backtest"]
    base_dir = os.path.dirname(os.path.abspath(__file__))

    for d in directories:
        path = os.path.join(base_dir, d)
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Directory created: {path}")

    # settings.py içerisindeki Telegram Token ve Chat ID'nin boş olmadığını doğrula
    if not config.TELEGRAM_TOKEN or not config.CHAT_ID:
        print("CRITICAL ERROR: TELEGRAM_TOKEN or CHAT_ID is empty in config/settings.py (or environment variables).")
        print("Lütfen Telegram kimlik bilgilerinizi tanımlayın ve tekrar deneyin.")
        sys.exit(1)

async def main():
    # 1. Ortam ve dizinleri hazırla
    verify_environment()

    # 2. Loglama kurulumu (core/logger.py içinden otomatik çağrılır ancak başlatıldığından emin olalım)
    from core.logger import setup_logger
    setup_logger()
    logger.info("Starting BIST Algorithmic Trading Bot Initialization...")

    # 3. Bileşenleri Başlat (DI - Dependency Injection)
    state_manager = StateManager()
    db_manager = DatabaseManager() # SQLite tablolarının varlığını doğrular
    notifier = TelegramNotifier()
    paper_trader = PaperTrader(db_manager, notifier)

    # Bot Komut Yöneticisi
    bot_manager = TelegramBotManager(db_manager)

    # Scheduler
    scheduler = MainScheduler(
        db_manager=db_manager,
        data_router=None, # Henüz başlatmadık ama modüler ilerleyebilir
        orchestrator=None,
        paper_trader=paper_trader,
        notifier=notifier,
        state_manager=state_manager
    )

    # 4. Sistemin Hazır Olduğunu Telegram'a Bildir
    msg = "🚀 *BİST Algoritmik Sinyal Motoru başlatıldı.*\n\n" \
          "Sistem Mimarisi: %100 Hazır.\n" \
          "Risk parametreleri devrede."
    await notifier.send_system_alert(msg, level="INFO")

    # 5. Asenkron Telegram polling işlemini ve main_scheduler'ı aynı event loop içerisinde başlat
    logger.info("Starting Event Loop (Telegram Polling + Main Scheduler)...")

    try:
        # gather ile ikisini birden çalıştır (bot polling'i bloklamadan)
        await asyncio.gather(
            bot_manager.start_polling(),
            scheduler.run()
        )
    except KeyboardInterrupt:
        logger.info("Bot stopped manually by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"Fatal error in main event loop: {e}")
    finally:
         logger.info("Shutting down bot...")

if __name__ == "__main__":
    # Terminalde girmem gereken bash/cmd komutları
    print("==========================================================")
    print("SİSTEMİ ÇALIŞTIRMAK İÇİN GEREKLİ TERMİNAL KOMUTLARI:")
    print("1. Bağımlılıkları yükleyin:")
    print("   pip install -r requirements.txt")
    print("\n2. Ortam değişkenlerini tanımlayın (Örnek macOS/Linux):")
    print("   export TELEGRAM_TOKEN='sizin_tokeniniz'")
    print("   export CHAT_ID='sizin_id_niz'")
    print("   (Windows PowerShell için: $env:TELEGRAM_TOKEN='...')")
    print("\n3. Sistemi Başlatın:")
    print("   python run_bot.py")
    print("==========================================================")

    # Sadece print'leri gösterip çıkmasını istemiyorsak, ortamda token varsa çalışsın:
    if os.getenv("TELEGRAM_TOKEN"):
         asyncio.run(main())
