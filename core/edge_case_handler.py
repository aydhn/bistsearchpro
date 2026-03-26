import logging

logger = logging.getLogger(__name__)

class EdgeCaseHandler:
    """
    Borsa İstanbul'a (BİST) özgü mikro yapı anormalliklerini
    (Tavan/Taban serileri, manipülatif hacim sıçramaları) tespit eden
    ve strategy.py sinyal üretse bile engelleme yetkisine sahip güvenlik katmanı.
    """

    @staticmethod
    def is_safe_to_trade(symbol: str, current_price: float, previous_close: float, current_volume: float, avg_volume_20d: float) -> bool:
        """
        Gelen anlık fiyatı (current_price) bir önceki günün kapanışıyla (previous_close)
        karşılaştırarak Tavan (+%9.9) veya Taban (-%9.9) durumunu kontrol eder.

        Ayrıca, son 1 saatlik (veya günlük) hacim, 20 günlük ortalama hacmin
        %500 (5 katı) üzerine çıkmış ve fiyat %5'ten fazla yön değiştirmişse,
        Devre Kesici (Halt) veya manipülasyon riski nedeniyle işlemi pas geçer.

        Args:
            symbol (str): Hisse sembolü
            current_price (float): Anlık Fiyat
            previous_close (float): Önceki Kapanış
            current_volume (float): Anlık (veya son periyot) Hacim
            avg_volume_20d (float): 20 Günlük Ortalama Hacim

        Returns:
            bool: İşlem yapmak güvenliyse True, değilse False.
        """
        if previous_close <= 0 or current_price <= 0:
             logger.warning(f"EdgeCaseHandler ({symbol}): Geçersiz fiyat verisi.")
             return False

        try:
            # 1. Tavan / Taban (Limit Up / Limit Down) Filtresi
            # BİST marj limitleri %10'dur (Pratikte %9.9 küsur).
            price_change_pct = ((current_price - previous_close) / previous_close) * 100.0

            if price_change_pct >= 9.9 or price_change_pct <= -9.9:
                logger.critical(f"İşlem İptali: {symbol} Tavan/Taban marjında ({price_change_pct:.2f}%). Likidite yok!")
                return False

            # 2. Devre Kesici (Halt) / Manipülasyon Tahmini Filtresi
            # Hacim anomalisi (Pump & Dump)
            if avg_volume_20d > 0:
                volume_surge = current_volume / avg_volume_20d

                # Hacim 5 katından fazla artmış ve fiyat değişimi > %5 ise (veya < -%5)
                if volume_surge >= 5.0 and abs(price_change_pct) > 5.0:
                    logger.warning(f"İşlem İptali: {symbol} Hacim anomalisi "
                                   f"(% {volume_surge * 100:.0f} artış) ve yüksek volatilite "
                                   f"(% {price_change_pct:.2f} değişim). Devre kesici / Manipülasyon riski!")
                    return False

            # Tüm testleri geçerse güvenlidir
            return True

        except Exception as e:
            logger.error(f"EdgeCaseHandler hesaplama hatası ({symbol}): {e}")
            return False

    """
    [QUANT MİMARI NOTU - BİST LİMİTLERİ (MARJ) VE LİKİDİTE KURUMASI]
    Birçok teknik strateji, güçlü momentum barlarında 'Long' sinyali verir.
    Ancak Borsa İstanbul'da bir hisse %10 yükseldiğinde Tavan (Limit Up) olur
    ve tavanda milyonlarca lot 'Alıcı' beklerken hiç 'Satıcı' kalmaz.
    Likidite kurumuş demektir.

    Eğer stratejiniz tam bu anda "Al" emri gönderirse (Piyasa Emri ile),
    emriniz sıraya girer ve yüksek ihtimalle gerçekleşmez. Gerçekleştiği an
    ise genelde 'Tavanın bozulduğu', yani akıllı paranın satışa geçtiği andır.

    Bu EdgeCaseHandler modülü, kağıt üzerinde (backtest'te) kârlı görünen
    ama gerçek hayatta likidite yetersizliğinden veya anlık hacim
    manipülasyonlarından kaynaklanan çöküşleri engeller.
    """
