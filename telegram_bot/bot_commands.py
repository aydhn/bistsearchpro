import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config.settings import config
from core.state_manager import StateManager
from data.db_manager import DatabaseManager
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramBotManager:
    """
    Çift Yönlü Telegram Dinleyicisi (Remote Command Center)
    Sadece bildirim göndermekle kalmaz, yetkili kullanıcıdan (/durum, /rapor, /durdur, /baslat)
    komutlarını dinleyerek otonom döngüye uzaktan müdahale edilmesine (Kill Switch) izin verir.
    """
    def __init__(self, db_manager: DatabaseManager):
        self.token = config.TELEGRAM_TOKEN
        self.allowed_chat_id = str(config.CHAT_ID)
        self.db = db_manager
        self.state_manager = StateManager()
        self.start_time = datetime.now()

        # Build application (v20+ format)
        if self.token:
            self.app = Application.builder().token(self.token).build()
            self._setup_handlers()
        else:
            logger.error("TELEGRAM_TOKEN eksik, CommandHandler başlatılamadı.")
            self.app = None

    def _setup_handlers(self):
        """Tüm komut dinleyicilerini (handlers) ekler."""
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("durum", self.cmd_durum))
        self.app.add_handler(CommandHandler("rapor", self.cmd_rapor))
        self.app.add_handler(CommandHandler("durdur", self.cmd_durdur))
        self.app.add_handler(CommandHandler("baslat", self.cmd_baslat))

    async def _check_auth(self, update: Update) -> bool:
        """Sadece izin verilen chat_id'den gelen komutları işler."""
        chat_id = str(update.effective_chat.id)
        if chat_id != self.allowed_chat_id:
            logger.warning(f"Yetkisiz Telegram Erişimi (Chat ID: {chat_id})")
            return False
        return True

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return

        msg = "👋 BIST Quant Alpha Botuna Hoşgeldiniz.\n\n" \
              "Komutlar:\n" \
              "/durum - Sistemin güncel piyasa rejimini ve çalışma süresini gösterir.\n" \
              "/rapor - Sanal portföy durumunu ve kâr/zarar özetini verir.\n" \
              "/durdur - (Kill Switch) Sinyal üretimini acil durdurur.\n" \
              "/baslat - Uyku modundaki sistemi aktif taramaya geçirir."
        await update.message.reply_text(msg)

    async def cmd_durum(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return

        uptime = datetime.now() - self.start_time
        days, remainder = divmod(uptime.total_seconds(), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{int(days)}g {int(hours)}s {int(minutes)}d"

        state = self.state_manager.get_state()
        halt_status = "🔴 DURDURULDU (Paused)" if state.get("emergency_halt") else "🟢 AKTİF (Running)"

        # Son piyasa rejimini DB'den çek
        last_regime = "Bilinmiyor"
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT market_regime FROM trade_journal ORDER BY id DESC LIMIT 1")
                row = cursor.fetchone()
                if row:
                    last_regime = "Boğa (BULL)" if row[0] == "BULL" else "Ayı (BEAR)"
        except Exception:
            pass

        msg = f"📊 *SİSTEM DURUMU*\n\n" \
              f"Çalışma Süresi (Uptime): {uptime_str}\n" \
              f"Tarama Modu: {halt_status}\n" \
              f"Son XU100 Rejimi: {last_regime}"

        await update.message.reply_markdown(msg)

    async def cmd_rapor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                # Bakiye
                cursor.execute("SELECT balance FROM paper_wallet WHERE id = 1")
                bal_row = cursor.fetchone()
                balance = bal_row[0] if bal_row else 0.0

                # Açık Pozisyonlar
                cursor.execute("SELECT symbol, entry_price, lot_size FROM open_positions")
                open_pos = cursor.fetchall()

                invested = 0.0
                for row in open_pos:
                    invested += (row[1] * row[2])

                total_equity = balance + invested
                cash_pct = (balance / total_equity) * 100.0 if total_equity > 0 else 100.0
                invest_pct = (invested / total_equity) * 100.0 if total_equity > 0 else 0.0

                # Kapalı işlemler kâr/zarar toplamı
                cursor.execute("SELECT SUM(pnl) FROM trade_journal WHERE status = 'CLOSED'")
                pnl_row = cursor.fetchone()
                total_pnl = pnl_row[0] if pnl_row and pnl_row[0] else 0.0

            msg = f"💼 *PORTFÖY RAPORU*\n\n" \
                  f"Toplam Varlık: {total_equity:.2f} TL\n" \
                  f"Net Kâr/Zarar: {total_pnl:.2f} TL\n" \
                  f"Nakit: {balance:.2f} TL (%{cash_pct:.1f})\n" \
                  f"Hissede: {invested:.2f} TL (%{invest_pct:.1f})\n" \
                  f"Açık Pozisyon Sayısı: {len(open_pos)}"

            await update.message.reply_markdown(msg)
        except Exception as e:
            await update.message.reply_text(f"Rapor oluşturulurken hata: {e}")

    async def cmd_durdur(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return

        # Kill Switch aktif
        self.state_manager.set_emergency_halt(True)
        logger.critical("Sistem uzaktan (Kill Switch) DURDURULDU.")
        await update.message.reply_text("🔴 Sistem başarıyla uyku moduna alındı. Sinyal araması durduruldu.")

    async def cmd_baslat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return

        # Sistemi aktif et
        self.state_manager.set_emergency_halt(False)
        logger.info("Sistem uzaktan tekrar BAŞLATILDI.")
        await update.message.reply_text("🟢 Sistem taramaya devam ediyor.")

    async def start_polling(self):
        """Asenkron olarak botu dinlemeye başlatır (run_bot.py içinde gather ile çağrılır)."""
        if self.app:
            logger.info("Telegram komut dinleyicisi başlatıldı.")
            # run_polling metodu bloklayıcı olduğu için (Eski versiyonlarda),
            # v20+'da start() ve stop() veya run_polling kullanılabilir.
            # Ancak arka planda paralel çalıştırmak için async with veya updater kullanıyoruz.
            # `initialize`, `start` ve `updater.start_polling` manuel yönetimi:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            logger.info("Bot polling (dinleme) devrede...")
            # Bu fonksiyon bitmesin diye sonsuz döngü (main_scheduler gibi) gerekmez çünkü
            # run_bot.py içinde asyncio.gather ile bir sonsuz döngü (scheduler) çalışacak.
            # Ancak polling'in arka planda task olarak yaşaması için:
            # await asyncio.Event().wait() kullanılabilir.
        else:
            logger.warning("Telegram Bot uygulaması başlatılamadı.")

    """
    [QUANT MİMARI NOTU - KILL SWITCH VE HUMAN-IN-THE-LOOP]
    Algoritmik ticarette "Siyah Kuğu" (Black Swan) olayları her an yaşanabilir.
    Ekranda beklenmedik bir flaş çöküş (Flash Crash) gördüğünüzde veya olağanüstü
    bir haber düştüğünde, terminale koşup süreçleri (process) kill etmekle vakit
    kaybedemezsiniz.

    Yasal ve finansal uyum (compliance) çerçevesinde her algoritmik sistemin
    bir 'Manuel Müdahale' şalteri olmalıdır. "Human-in-the-loop" (İnsanın döngüde olması),
    yapay zekaya gözü kapalı güvenmek yerine nihai kontrolü fon yöneticisinde tutar.
    /durdur komutu, BİST'te devre kesicilerin yetersiz kaldığı ekstrem panik anlarında
    sistemin intihar etmesini (sürekli alım denemesini) engeller.
    """
