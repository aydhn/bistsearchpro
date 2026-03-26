import logging
from data.db_manager import DatabaseManager
from telegram_bot.notifier import TelegramNotifier

logger = logging.getLogger(__name__)

class StateRecoveryManager:
    """
    Felaket Kurtarma ve Durum Hatırlayıcı (Crash Recovery).
    Sistem kapandığında, çöktüğünde veya bilgisayar yeniden başlatıldığında,
    veritabanındaki açık işlemleri ve o anki Stop-Loss / Take-Profit seviyelerini
    RAM'e (hafızaya) geri yükler.
    Ayrıca sistem çevrimdışıyken fiyat stop seviyesini geçmişse bunu tespit edip
    acil uyarı gönderir.
    """
    def __init__(self, db_manager: DatabaseManager, notifier: TelegramNotifier):
        self.db = db_manager
        self.notifier = notifier

    async def recover_state(self, fetcher):
        """
        Sistemin açılış anında (main döngüsü başlamadan önce) çalıştırılır.
        Veritabanından açık işlemleri okur, o anki güncel fiyatları (fetcher ile) kontrol eder.

        Args:
            fetcher: O anki güncel hisse fiyatını çekecek modül (YfDataEngine)
        """
        logger.info("Felaket Kurtarma (State Recovery) Modülü: Açık pozisyonlar taranıyor...")

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, symbol, direction, stop_loss, take_profit, entry_price FROM open_positions")
                open_trades = cursor.fetchall()

            if not open_trades:
                logger.info("Kurtarılacak açık pozisyon bulunamadı. Sistem temiz başlıyor.")
                return

            logger.info(f"Sistem {len(open_trades)} adet açık pozisyonla yeniden başlatıldı. Durumları doğrulanıyor...")

            # Gecikmiş çıkışları (Crash Gap) tespit et
            for trade in open_trades:
                t_id, symbol, direction, sl, tp, entry_price = trade

                try:
                    # En güncel 1 dakikalık kapanış fiyatını (veya 1 saatlik) alarak kontrol et
                    df = fetcher.fetch_ohlcv(symbol, interval="1d", n_bars=1)
                    if df.empty:
                        logger.warning(f"Durum onayı yapılamadı (Veri yok): {symbol}")
                        continue

                    current_price = df['close'].iloc[-1]

                    if direction.upper() == "BUY":
                        if current_price <= sl:
                            msg = f"⚠️ Gecikmiş Çıkış Bildirimi (Crash Recovery):\n\n{symbol} çevrimdışıyken Stop-Loss ({sl:.2f}) seviyesini ihlal etmiş. Anlık Fiyat: {current_price:.2f}. Lütfen pozisyonu manuel olarak acil kapatın!"
                            logger.critical(msg)
                            await self.notifier.send_system_alert(msg, level="CRITICAL")
                        elif current_price >= tp:
                            msg = f"✅ Kâr Al Bildirimi (Crash Recovery):\n\n{symbol} çevrimdışıyken Take-Profit ({tp:.2f}) seviyesine ulaşmış. Anlık Fiyat: {current_price:.2f}. Pozisyonu kapatabilirsiniz."
                            logger.info(msg)
                            await self.notifier.send_system_alert(msg, level="INFO")
                except Exception as e:
                    logger.error(f"Gecikmiş çıkış kontrolünde (Crash Recovery) hata ({symbol}): {e}")

        except Exception as e:
            logger.error(f"State Recovery taraması sırasında hata: {str(e)}")

    """
    [QUANT MİMARI NOTU - DURUM KURTARMA (STATE / CRASH RECOVERY)]
    Yerel bir makinede çalışan botların en büyük zaafı "Uptime" (Kesintisiz çalışma)
    sorunudur. Elektrik kesintisi, Windows Güncellemesi veya Python çökmesi kaçınılmazdır.
    Eğer bot, açıldığında "Nerede kalmıştım?" sorusuna cevap veremiyorsa,
    milyonlarca liralık pozisyonlarınızı kör (Unmonitored) bırakmış demektir.

    State Recovery, veritabanına ACID kurallarıyla yazılan kalıcı (Persistent) durumu okur.
    Eğer elektrik yokken piyasada büyük bir kırılım yaşanmış ve THYAO hissesindeki Stop-Loss
    seviyeniz %5 ihlal edilmişse, bot açıldığı ilk saniyede bunu fark eder ve Telegram
    üzerinden telefonunuza kırmızı alarm (CRITICAL) gönderir. Bu modül, uyum (compliance)
    süreçleri için bir zorunluluktur.
    """
