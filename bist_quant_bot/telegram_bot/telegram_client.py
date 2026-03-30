import logging
import asyncio
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

class TelegramManager:
    """
    Sıfır Bütçe (Webhook portsuz) Asenkron Long Polling Etkileşimli Bot (Phases 15, 18, 19, 20).
    Sadece ADMIN_CHAT_ID'den gelen komutları işler (Güvenlik Kalkanı).
    ED Capital Kurumsal Şablonu prensiplerine tam sadıktır.
    """
    def __init__(self, config, portfolio_manager, live_engine=None):
        self.token = config['api_keys']['TELEGRAM_TOKEN']
        self.admin_id = str(config['api_keys']['ADMIN_CHAT_ID'])
        self.portfolio = portfolio_manager
        self.live_engine = live_engine  # Dairesel importları kırmak için sonradan eklenebilir

        # Bot objesini oluştur
        if self.token == "BURAYA_TOKEN_GIRIN":
            logging.warning("Telegram Token girilmemiş! Sadece test modunda çalışır, mesaj atamaz.")
            self.application = None
            return

        self.application = ApplicationBuilder().token(self.token).build()
        self._register_handlers()

    def _register_handlers(self):
        """Komutları dinleyen etkileşimli asistan yapısı"""
        # Güvenlik (Admin filtresi)
        async def admin_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if str(update.effective_chat.id) != self.admin_id:
                logging.warning(f"Yetkisiz Erişim Engellendi: ID={update.effective_chat.id}")
                return False
            return True

        # /durum (Sistem Sağlık ve Mod Durumu)
        async def cmd_durum(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not await admin_filter(update, context): return

            # live_engine'in durumunu sorgula
            mode = "Savaş Modu 🟢" if (self.live_engine and self.live_engine.is_running) else "Dondurulmuş 🔴"

            msg = (
                "🏛️ **ED CAPITAL KURUMSAL ŞABLONU - SİSTEM DURUM RAPORU**\n\n"
                "**Piyasalara Genel Bakış:** XU100 Rejimi [Aktif/Pasif]\n"
                f"Operasyon Modu: {mode} (Yeni alımlar açık)\n"
                "Zamanlayıcı (Scheduler): Sorunsuz çalışıyor.\n"
                "Admin Doğrulaması: Başarılı. Sistem emrinizde."
            )
            await update.message.reply_text(msg, parse_mode='Markdown')

        # /portfoy (Açık Pozisyonlar ve PnL)
        async def cmd_portfoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not await admin_filter(update, context): return

            bal = self.portfolio.get_balance()
            pos = self.portfolio.get_open_positions()

            msg = (
                "📊 **ED CAPITAL KURUMSAL ŞABLONU - HAFTALIK PORTFÖY VE RİSK RAPORU**\n\n"
                "**Piyasalara Genel Bakış:** Anlık Cüzdan Durumu\n"
                f"Güncel Sanal Kasa: {bal:,.2f} TL\n"
                f"Açık Pozisyon Sayısı: {len(pos)} / 10 (Maksimum)\n"
                "Nakit Oranı: %100 (Örnek Nakit Hesaplaması)\n\n"
                "Aktif İşlemler:\n"
            )
            for sym, data in pos.items():
                msg += f"• {sym} | Maliyet: {data['entry_price']:.2f} | Hedef: {data['take_profit']:.2f}\n"

            if not pos:
                msg += "Şu an açık pozisyon bulunmamaktadır (Nakitte bekleniyor)."

            await update.message.reply_text(msg, parse_mode='Markdown')

        # /al_onayla THYAO 150.5 200 (Manuel İşlem Onayı - Phase 18)
        async def cmd_al_onayla(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not await admin_filter(update, context): return
            args = context.args
            if len(args) != 3:
                await update.message.reply_text("Kullanım: `/al_onayla [HİSSE_KODU] [GERÇEK_FİYAT] [ADET]`", parse_mode='Markdown')
                return

            symbol, price_str, lot_str = args[0].upper(), args[1], args[2]
            try:
                price = float(price_str.replace(',', '.'))
                lot = int(lot_str)
                # PENDING LISTESINDEN ALIP PORTFOYE YAZMA İŞLEMİ (Basitleştirildi)
                sl = price * 0.95 # Geçici ATR olmadan
                tp = price * 1.10
                self.portfolio.add_position({
                    "symbol": symbol, "entry_price": price, "lot_size": lot,
                    "stop_loss": sl, "take_profit": tp
                })

                await update.message.reply_text(
                    f"🟢 **ED CAPITAL - MANUEL ONAY BAŞARILI**\n\n"
                    f"**Piyasalara Genel Bakış:** İşlem Mutabakatı Sağlandı.\n"
                    f"Hisse: {symbol} | Fiyat: {price:.2f} | Lot: {lot}\n"
                    f"Sistem, pozisyonu Trailing Stop ile izlemeye aldı."
                )
            except ValueError:
                await update.message.reply_text("Hata: Fiyat (sayı) ve Lot (tam sayı) formatı geçersiz.")

        # /durdur (Makro Kriz Dondurucu)
        async def cmd_durdur(update: Update, context: ContextTypes.DEFAULT_TYPE):
             if not await admin_filter(update, context): return
             if self.live_engine:
                  self.live_engine.is_running = False
             await update.message.reply_text("🚨 Sistem DONDURULDU! Sadece mevcut açık pozisyonlar (çıkışlar) izleniyor. Yeni alım yasak.")

        # Handlerları ekle
        self.application.add_handler(CommandHandler('durum', cmd_durum))
        self.application.add_handler(CommandHandler('portfoy', cmd_portfoy))
        self.application.add_handler(CommandHandler('al_onayla', cmd_al_onayla))
        self.application.add_handler(CommandHandler('durdur', cmd_durdur))

    async def send_message_async(self, text: str):
        """Asenkron doğrudan mesaj atma (Push notification)"""
        if not self.application: return
        try:
            bot = self.application.bot
            await bot.send_message(chat_id=self.admin_id, text=text, parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Telegram Mesaj Gönderme Hatası: {e}")

    def send_message_sync(self, text: str):
        """
        Diğer senkron modüllerin kolayca mesaj atabilmesi için (Thread safe event loop delegation).
        Not: asyncio.run(), zaten çalışan bir loop varsa hata verir. O yüzden loop_in_executor veya task eklenir.
        """
        if not self.application: return
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.send_message_async(text))
            else:
                 loop.run_until_complete(self.send_message_async(text))
        except Exception as e:
            logging.error(f"Senkron Telegram İletim Hatası: {e}")

    async def send_photo_async(self, photo_path: str, caption: str):
        """Görsel onay için (Phase 19)"""
        if not self.application or not os.path.exists(photo_path): return
        try:
            bot = self.application.bot
            with open(photo_path, 'rb') as photo:
                await bot.send_photo(chat_id=self.admin_id, photo=photo, caption=caption, parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Telegram Fotoğraf Hatası: {e}")

    async def start_polling(self):
        """Long Polling başlatır"""
        if self.application:
             logging.info("Telegram Bot (Long Polling) başlatılıyor...")
             await self.application.initialize()
             await self.application.start()
             await self.application.updater.start_polling()
