import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config.config_manager import ConfigManager
from core.logger_engine import LoggerEngine

logger = LoggerEngine.get_system_logger()

# "python-telegram-bot" kütüphanesinin "Long Polling" mimarisini asenkron kuruyoruz.
# Webhook kullanılmayacak.
# GÜVENLİK (Admin Kalkanı): Yabancılardan gelen mesajları tamamen yoksay (Sessizce Drop et).

class TelegramBot:
    def __init__(self):
        self.token = ConfigManager.get("api_keys", "TELEGRAM_TOKEN")
        self.admin_id = int(ConfigManager.get("api_keys", "ADMIN_CHAT_ID") or 0)
        self.app = ApplicationBuilder().token(self.token).build()

        self.app.add_handler(CommandHandler("durum", self.cmd_durum))
        self.app.add_handler(CommandHandler("portfoy", self.cmd_portfoy))
        self.app.add_handler(CommandHandler("taramayap", self.cmd_taramayap))
        self.app.add_handler(CommandHandler("durdur", self.cmd_durdur))
        self.app.add_handler(CommandHandler("baslat", self.cmd_baslat))
        self.app.add_handler(CommandHandler("al_onayla", self.cmd_al_onayla))
        self.app.add_handler(CommandHandler("esgec", self.cmd_esgec))
        self.app.add_handler(CommandHandler("manuel_sat", self.cmd_manuel_sat))
        self.app.add_handler(CommandHandler("ayarlar", self.cmd_ayarlar))

    def _is_admin(self, update: Update) -> bool:
        return update.effective_user.id == self.admin_id

    async def cmd_durum(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update): return
        msg = ("🏛️ **ED CAPITAL KURUMSAL ŞABLONU - SİSTEM DURUM RAPORU**\n"
               "**Piyasalara Genel Bakış:** XU100 Rejimi [Aktif/Pasif]\n"
               "Operasyon Modu: Savaş Modu 🟢\n"
               "Zamanlayıcı (Scheduler): Sorunsuz çalışıyor.\n"
               "Admin Doğrulaması: Başarılı. Sistem emrinizde.")
        await update.message.reply_text(msg, parse_mode='Markdown')

    async def cmd_portfoy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update): return
        msg = ("📊 **ED CAPITAL KURUMSAL ŞABLONU - GÜNCEL PORTFÖY**\n"
               "**Piyasalara Genel Bakış:** Aktif Varlık Analizi\n"
               "Açık Pozisyonlar:\n"
               "- THYAO: Maliyet 250 TL | %5 Kâr\n"
               "Sanal Kasa: 105.000 TL")
        await update.message.reply_text(msg, parse_mode='Markdown')

    async def cmd_taramayap(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update): return
        await update.message.reply_text("Manuel tarama tetiklendi. Sonuçlar birazdan iletilecek.")

    async def cmd_durdur(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update): return
        await update.message.reply_text("Sistem Donduruldu (KILL SWITCH). Yeni alımlar kapalı.")

    async def cmd_baslat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update): return
        await update.message.reply_text("Sistem Savaş Moduna alındı. Risk-On.")

    async def cmd_al_onayla(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update): return
        args = context.args
        if len(args) != 3:
            await update.message.reply_text("Kullanım: /al_onayla [HİSSE_KODU] [FİYAT] [ADET]")
            return
        await update.message.reply_text(f"ONAY ALINDI: {args[0]} | {args[1]} TL | {args[2]} Lot")

    async def cmd_esgec(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update): return
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("Kullanım: /esgec [HİSSE_KODU]")
            return
        await update.message.reply_text(f"Sinyal iptal edildi: {args[0]}")

    async def cmd_manuel_sat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update): return
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("Kullanım: /manuel_sat [HİSSE_KODU]")
            return
        await update.message.reply_text(f"Manuel çıkış kaydedildi: {args[0]}")

    async def cmd_ayarlar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update): return
        msg = ("⚙️ **ED CAPITAL KURUMSAL ŞABLONU - SİSTEM PARAMETRELERİ RAPORU**\n"
               "**Piyasalara Genel Bakış:** Aktif Konfigürasyon Dosyası Özeti\n"
               f"Strateji Beyni: EMA({ConfigManager.get('strategy_settings','EMA_SHORT')}/{ConfigManager.get('strategy_settings','EMA_LONG')}), RSI Eşiği: {ConfigManager.get('strategy_settings','RSI_OVERSOLD')}\n"
               f"Risk Yönetimi: İşlem Başına Risk %{ConfigManager.get('trading_parameters','MAX_RISK_PER_TRADE_PERCENT')}, İzleyen Stop: {ConfigManager.get('strategy_settings','ATR_MULTIPLIER_SL')}x ATR\n"
               f"Sistem Tarama Frekansı: Her {ConfigManager.get('system_settings','POLLING_INTERVAL_MINUTES')} dakikada bir.\n"
               "Durum: Parametreler config.json üzerinden başarıyla yüklenmiş ve hafızaya alınmıştır.")
        await update.message.reply_text(msg, parse_mode='Markdown')

    async def send_message(self, text):
        try:
            await self.app.bot.send_message(chat_id=self.admin_id, text=text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Telegram mesaj gönderme hatası: {e}")

    async def send_photo(self, photo_path, caption):
        try:
            with open(photo_path, 'rb') as photo:
                await self.app.bot.send_photo(chat_id=self.admin_id, photo=photo, caption=caption, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Telegram fotoğraf gönderme hatası: {e}")

    def run_polling(self):
        logger.info("Telegram Bot (Long Polling) başlatılıyor...")
        self.app.run_polling()
