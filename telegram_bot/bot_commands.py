import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config.settings import config
from data.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class TelegramBotManager:
    """
    Kullanıcının Telegram üzerinden asenkron komutlar vermesini sağlayan,
    çift yönlü iletişim katmanı. /status, /report, /analyze destekler.
    """
    def __init__(self, db_manager: DatabaseManager):
        self.token = config.TELEGRAM_TOKEN
        self.chat_id = config.CHAT_ID
        self.db = db_manager

        if not self.token:
            logger.critical("Telegram token is missing. Bot cannot start.")
            return

        self.app = Application.builder().token(self.token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CommandHandler("report", self.report_command))
        self.app.add_handler(CommandHandler("analyze", self.analyze_command))
        # Hata yakalayıcı
        self.app.add_error_handler(self.error_handler)

    async def _check_auth(self, update: Update) -> bool:
        """Kullanıcının yetkili olup olmadığını kontrol et."""
        user_id = str(update.effective_user.id)
        if user_id != str(self.chat_id):
            logger.warning(f"Unauthorized user {user_id} tried to use bot.")
            await update.message.reply_text("⛔ Yetkisiz erişim reddedildi.")
            return False
        return True

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        msg = "🤖 BİST Algoritmik Sinyal Botu Devrede.\n\n" \
              "Komutlar:\n" \
              "/status - Sistem Sağlığı\n" \
              "/report - Açık Pozisyonlar ve PnL\n" \
              "/analyze <SEMBOL> - Anlık Teknik Analiz Özeti"
        await update.message.reply_text(msg)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return

        # Gelecekte StateManager'dan okunacak. Şimdilik mock veri.
        sys_state = "AKTİF"
        regime = "Bilinmiyor" # Normalde RegimeFilter veya Brain'den gelir

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM paper_wallet WHERE id = 1")
            row = cursor.fetchone()
            balance = row[0] if row else 0.0

        msg = f"🟢 Sistem Durumu: {sys_state}\n" \
              f"📊 Piyasa Rejimi: {regime}\n" \
              f"💰 Cüzdan Bakiyesi: {balance:.2f} TL"
        await update.message.reply_text(msg)

    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT symbol, direction, entry_price, lot_size FROM open_positions")
            positions = cursor.fetchall()

        if not positions:
            await update.message.reply_text("📭 Şu an açık pozisyon bulunmuyor.")
            return

        report_lines = ["📋 *AÇIK POZİSYONLAR*\n\n"]
        for p in positions:
            sym, dir_, entry, lot = p
            report_lines.append(f"🔹 {sym} | {dir_} | Giriş: {entry:.2f} | Lot: {lot}\n")

        report = "".join(report_lines)

        await update.message.reply_text(report, parse_mode='Markdown')

    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return

        args = context.args
        if not args:
            await update.message.reply_text("Lütfen bir sembol girin. Örn: /analyze THYAO")
            return

        symbol = args[0].upper()
        # Burada DataRouter ve IndicatorPipeline çağrılıp analiz yapılabilir.
        # Basitlik adına sadece mesaj dönüyoruz. Sistemin geri kalanı main_scheduler üzerinden çalışır.
        await update.message.reply_text(f"🔍 {symbol} için analiz isteği alındı. (Bu özellik, arka plan işlemleriyle entegre edilecek.)")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(f"Telegram Bot Error: {context.error}")

    async def start_polling(self):
        """Asenkron event loop içerisinde sürekli dinleme başlatır."""
        logger.info("Telegram Bot Polling başlatılıyor...")
        if self.app:
             await self.app.initialize()
             await self.app.start()
             await self.app.updater.start_polling(drop_pending_updates=True)
             # Uygulamanın sonsuza kadar çalışması için:
             # run_bot.py içerisinde asyncio.gather(app.updater.start_polling(), scheduler()) kullanılmalı.
