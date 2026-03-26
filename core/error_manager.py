import logging
import traceback
import time
import functools
import sqlite3
from typing import Callable, Any
from telegram_bot.notifier import TelegramNotifier
from core.state_manager import StateManager

logger = logging.getLogger(__name__)

class ErrorManager:
    """
    Kurumsal Hata Ayıklama (Advanced Error Handling) ve Dayanıklılık (Resilience) Katmanı.
    "try-except-pass" gibi fail-silent (sessizce çökme) amatörlüklerini önler.
    Katlanarak artan bekleme (Exponential Backoff) süreleri ve kritik veritabanı kilitlenme
    durumlarında acil Kill-Switch (Durdurma) mekanizmasını barındırır.
    """
    def __init__(self, notifier: TelegramNotifier, state_manager: StateManager):
        self.notifier = notifier
        self.state_manager = state_manager

    async def handle_critical_error(self, error: Exception, context_msg: str):
        """
        Kritik hataları (Örn: Veritabanı kilitlenmesi, disk dolması) yakalar,
        Stack Trace ile kaydeder ve sistemi durdurup acil Telegram bildirimi atar.
        """
        error_msg = f"{context_msg}\nHata: {str(error)}"
        trace = traceback.format_exc()

        logger.critical(f"🚨 KRİTİK SİSTEM HATASI: {error_msg}\n{trace}")

        # Kill Switch'i tetikle
        self.state_manager.set_emergency_halt(True)
        logger.critical("Sistem güvenlik amacıyla DURDURULDU (Kill Switch Aktif).")

        # Telegram'a bildir
        alert_msg = f"🚨 *KRİTİK SİSTEM HATASI* 🚨\n\n{error_msg}\n\nAna döngü durduruldu. Acil müdahale gerekli!"
        await self.notifier.send_system_alert(alert_msg, level="CRITICAL")

def exponential_backoff(retries=4, base_delay=2.0, max_delay=32.0):
    """
    Ağ isteklerine (API, Telegram, vb.) özel Katlanarak Artan Bekleme Süresi (Exponential Backoff) Dekoratörü.
    Önce 2 saniye, sonra 4 saniye, sonra 8 saniye, en son 16 saniye bekleyerek tekrar dener.
    Eğer max denemeye (retries) ulaşılırsa, sistemi çöktürmez, sadece exception fırlatır
    (Zarif Hizmet Kaybı - Graceful Degradation - ana döngüde yakalanıp pass geçilir).
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = base_delay
            last_exception = None

            for attempt in range(1, retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    # Eğer hata sqlite3 kilitlenmesiyse veya kritikse, bekleme. (Exponential Backoff genelde Network içindir)
                    if isinstance(e, sqlite3.OperationalError) and "database is locked" in str(e):
                        logger.warning(f"SQLite kilitlenmesi ({func.__name__}): Yeniden deneniyor... (Deneme {attempt}/{retries})")
                    else:
                        logger.warning(f"Ağ İsteği Hatası ({func.__name__}): {e}. {delay}s sonra tekrar denenecek. (Deneme {attempt}/{retries})")

                    if attempt < retries:
                        time.sleep(delay)
                        delay = min(delay * 2, max_delay) # Katlanarak artır (Örn: 2, 4, 8, 16)
                    else:
                        logger.error(f"Maksimum deneme ({retries}) aşıldı. İşlem başarısız: {func.__name__}")
                        # Çökme değil (Fail-Fast değil), Graceful Degradation için hatayı fırlat
                        # veya None dönebilir (Kullanım yerine bağlı).
                        raise last_exception
            return None # Should not be reached
        return wrapper
    return decorator

    """
    [QUANT MİMARI NOTU - FAIL-FAST VS. GRACEFUL DEGRADATION]
    Sıradan bir Python scripti API'den "Timeout" veya "502 Bad Gateway" aldığında
    ekrana kırmızı bir hata basıp kapanır (Fail-Fast). Buna amatörlük denir.

    Yatırım dünyasında robotunuzun çökme lüksü yoktur! Yfinance sunucusu
    2 dakikalığına göçerse (Rate-Limit vs.), sistem çökmek yerine önce 2 saniye
    bekler, olmazsa 4, sonra 8, sonra 16. (Exponential Backoff).
    Eğer yine olmazsa, "Tamam, THYAO hissesini bu saatlik döngüde pas geçiyorum,
    diğer hisseye geçeyim" der (Skip).

    Veya Yapay Zeka modeli yüklenemedi mi? "Ah, sklearn patladı!" deyip kapanmaz.
    ML Modülü "None" döner, Orkestratör bunu fark edip "Tamam, sadece teknik indikatörlere
    güvenerek işlem açayım" der. Buna Zarif Hizmet Kaybı (Graceful Degradation) denir.
    Sistem bir yerinden yaralansa bile savaşmaya devam eder.

    Ancak veritabanınız (SQLite) diskiniz dolduğu için "Locked" verdiyse, bu kritik bir
    durumdur (State Corruption riski). İşte o zaman "Fail-Fast" yaparsınız.
    Kill-Switch'e basıp ana şalteri indirirsiniz.
    """
