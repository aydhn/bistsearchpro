import logging
from core.state_manager import StateManager
from telegram_bot.notifier import TelegramNotifier
import asyncio

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Sistemin sağlığını denetler. Ardışık 3 başarısızlık veya
    sermaye çöküşünde (Max Drawdown > %15) sistemi EMERGENCY_HALT durumuna alır.
    """
    def __init__(self, state_manager: StateManager, notifier: TelegramNotifier, paper_trader):
        self.state_manager = state_manager
        self.notifier = notifier
        self.trader = paper_trader

        self.consecutive_failures = 0
        self.max_failures = 3

        # Basitlik için ilk bakiyeyi 100k kabul ediyoruz, normalde veritabanından alınmalı.
        # PaperTrader'dan güncel bakiyeyi okuyabiliriz.
        self.initial_balance = 100000.0

    async def record_failure(self):
        """Veri çekilemezse veya analiz patlarsa bu metod çağrılır."""
        self.consecutive_failures += 1
        logger.warning(f"Sistem Hatası Kaydedildi. Ardışık Başarısızlık: {self.consecutive_failures}/{self.max_failures}")

        if self.consecutive_failures >= self.max_failures:
            await self._trigger_halt("Ardışık 3 analiz döngüsünde veri çekilemedi veya hata alındı.")

    def record_success(self):
        """Döngü başarılı ise hata sayacını sıfırlar."""
        if self.consecutive_failures > 0:
             logger.info("Döngü başarılı, hata sayacı sıfırlanıyor.")
        self.consecutive_failures = 0

    async def check_health(self):
        """
        Zamanlayıcı tarafından periyodik olarak çağrılır ve cüzdan sağlığını (Max DD) denetler.
        """
        current_balance = self.trader.get_balance()

        if current_balance <= 0:
             await self._trigger_halt("Bakiye sıfırlandı veya okunamıyor!")
             return

        # %15 kayıp kontrolü
        loss_pct = (self.initial_balance - current_balance) / self.initial_balance

        if loss_pct > 0.15:
             await self._trigger_halt(f"Paper Wallet bakiyesi başlangıç değerinin %15 altına düştü! (Güncel: {current_balance:.2f} TL)")

    async def _trigger_halt(self, reason):
        """Sistemi acil durdurma moduna alır ve Telegram'a bildirir."""
        current_state = self.state_manager.get_state()
        if current_state.get("emergency_halt", False):
            # Zaten durmuş, tekrar mesaj atma
            return

        logger.critical(f"DEVRE KESİCİ TETİKLENDİ: {reason}")
        self.state_manager.update_state("emergency_halt", True)

        msg = f"🚨 *SİSTEM ACİL DURUM NEDENİYLE DURDURULDU* 🚨\n\n" \
              f"Sebep: {reason}\n\n" \
              f"Şalter inik olduğu sürece zamanlayıcı hiçbir fonksiyonu tetiklemeyecektir.\n" \
              f"Lütfen logları kontrol edin ve müdahale edin."

        await self.notifier.send_system_alert(msg, level="CRITICAL")
