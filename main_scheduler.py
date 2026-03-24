import schedule
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class MainScheduler:
    """
    Python'un schedule kütüphanesini kullanan, Borsa İstanbul
    mesai saatlerine göre işlemleri zamanlayan hafif bir araç.
    """
    def __init__(self, db_manager, data_router, orchestrator, paper_trader, notifier, state_manager):
        self.db = db_manager
        self.router = data_router
        self.orchestrator = orchestrator
        self.trader = paper_trader
        self.notifier = notifier
        self.state_manager = state_manager

        self.setup_jobs()

    def setup_jobs(self):
        # Her sabah 09:30'da veri ambarı güncellemesi
        schedule.every().day.at("09:30").do(self.run_daily_data_update)

        # Hafta içi saat 10:00 ile 18:00 arasında her saat başı tarama
        # schedule kütüphanesinde 'hours' veya 'minutes' ile spesifik zaman dilimi yönetimi
        # biraz manueldir. Basitlik adına her saat başı fonksiyonu çağırıp içeride saat kontrolü yapacağız.
        schedule.every().hour.at(":00").do(self.run_hourly_scan)

        # Her saat başı 15 geçe açık pozisyon kontrolü
        schedule.every().hour.at(":15").do(self.run_position_check)

        # Gün sonu özeti
        schedule.every().day.at("18:15").do(self.run_daily_summary)

        logger.info("Scheduler jobs setup complete.")

    def run_daily_data_update(self):
        logger.info("Executing daily data update...")
        # Burada tüm universe için veriler çekilip SQLite'a yazılır.

    def run_hourly_scan(self):
        now = datetime.now()
        # Hafta içi ve BIST mesai saatleri (10:00 - 18:00)
        if now.weekday() < 5 and 10 <= now.hour <= 18:
            state = self.state_manager.get_state()
            if state.get("emergency_halt", False):
                 logger.critical("SİSTEM ACİL DURUM NEDENİYLE DURDURULDU. Tarama atlanıyor.")
                 return

            logger.info("Executing hourly market scan...")
            # Sinyal tarama işlemleri
        else:
            logger.debug("Piyasa kapalı, saat başı tarama atlandı.")

    def run_position_check(self):
        now = datetime.now()
        if now.weekday() < 5 and 10 <= now.hour <= 18:
            logger.info("Executing open position check...")
            # Güncel fiyatları al ve trader.check_open_positions'ı tetikle
            # Şimdilik boş bir sözlük ile tetikleniyor. Veri bağlandığında güncellenecek.
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.trader.check_open_positions({}))
            except RuntimeError as e:
                logger.error(f"Event loop bulunamadı, pozisyon kontrolü atlandı: {e}")

    def run_daily_summary(self):
        now = datetime.now()
        if now.weekday() < 5:
            logger.info("Executing daily summary...")
            try:
                balance = self.trader.get_balance()
                msg = f"📊 *Gün Sonu Özeti*\n\nGüncel Sanal Bakiye: {balance:.2f} TL"
                loop = asyncio.get_running_loop()
                loop.create_task(self.notifier.send_system_alert(msg, level="INFO"))
            except RuntimeError as e:
                logger.error(f"Event loop bulunamadı, günlük özet atlandı: {e}")

    async def run(self):
        """Asenkron olay döngüsü ile çalışacak ana zamanlayıcı."""
        logger.info("MainScheduler loop started.")
        while True:
            schedule.run_pending()
            await asyncio.sleep(1) # CPU'yu yormamak için uyuma
