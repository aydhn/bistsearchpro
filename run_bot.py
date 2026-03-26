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
from core.state_recovery import StateRecoveryManager
from core.data_fetcher_yf import YfDataEngine

logger = logging.getLogger(__name__)

def verify_environment():
    directories = ["data", "data/models", "logs", "config", "core", "strategies", "telegram_bot", "backtest"]
    base_dir = os.path.dirname(os.path.abspath(__file__))

    for d in directories:
        path = os.path.join(base_dir, d)
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Directory created: {path}")

    if not config.TELEGRAM_TOKEN or not config.CHAT_ID:
        print("CRITICAL ERROR: TELEGRAM_TOKEN or CHAT_ID is empty.")
        print("Lütfen Telegram kimlik bilgilerinizi tanımlayın ve tekrar deneyin.")
        sys.exit(1)

async def main():
    verify_environment()

    from core.logger import setup_logger
    setup_logger()
    logger.info("Starting BIST Algorithmic Trading Bot Initialization...")

    state_manager = StateManager()
    db_manager = DatabaseManager()
    notifier = TelegramNotifier()
    paper_trader = PaperTrader(db_manager, notifier)
    fetcher = YfDataEngine()

    bot_manager = TelegramBotManager(db_manager)

    # Faz 17: Felaket Kurtarma (State Recovery)
    recovery_manager = StateRecoveryManager(db_manager, notifier)
    await recovery_manager.recover_state(fetcher)

    scheduler = MainScheduler(
        db_manager=db_manager,
        data_router=fetcher,
        orchestrator=None, # To be integrated inside main_scheduler's actual tick logic
        paper_trader=paper_trader,
        notifier=notifier,
        state_manager=state_manager
    )

    msg = "🚀 *BİST Algoritmik Sinyal Motoru başlatıldı.*\n\n" \
          "Sistem Mimarisi: 21 Fazlık Yapı Hazır.\n" \
          "Sanal Cüzdan ve Risk parametreleri devrede.\n" \
          "Komutlar için /start yazabilirsiniz."
    await notifier.send_system_alert(msg, level="INFO")

    logger.info("Starting Event Loop (Telegram Polling + Main Scheduler)...")

    try:
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
    if os.getenv("TELEGRAM_TOKEN"):
         asyncio.run(main())
    else:
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
