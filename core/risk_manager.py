import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RiskManager:
    """
    JP Morgan risk algısını yansıtan katı bir risk yöneticisi.
    Sinyalleri onaylar (veya reddeder), dinamik stop-loss ve kar-al noktalarını ATR'ye göre hesaplar,
    Trailing Stop, Breakeven, Kademeli Çıkış (Scale-Out) ve Zaman Aşımı (Time-Stop) mekanizmalarını barındırır.
    """
    def __init__(self):
        # ATR Çarpanları
        self.stop_loss_multiplier = 1.5
        self.take_profit_multiplier = 3.0
        # Min. R:R oranı (Örn: 1 birim riske karşı en az 2 birim ödül)
        self.min_risk_reward_ratio = 2.0

        # Dinamik Pozisyon Yönetimi Parametreleri
        self.max_holding_period_days = 10 # Bir hissede en fazla 10 iş günü beklenir

    def calculate_trade_parameters(self, entry_price: float, atr_value: float, direction: str = "LONG"):
        """
        ATR kullanarak dinamik Stop-Loss ve Take-Profit (Kar Al) seviyelerini belirler.
        Risk/Ödül oranı hesaplanıp 1:2'nin altındaysa "onaysız" olarak döner.
        """
        try:
            if direction == "LONG":
                stop_loss = entry_price - (self.stop_loss_multiplier * atr_value)
                take_profit = entry_price + (self.take_profit_multiplier * atr_value)
            else:
                stop_loss = entry_price + (self.stop_loss_multiplier * atr_value)
                take_profit = entry_price - (self.take_profit_multiplier * atr_value)

            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)

            if risk == 0:
                logger.warning("Risk sıfır olarak hesaplandı, işlem reddedildi.")
                return False, stop_loss, take_profit

            risk_reward_ratio = reward / risk

            if risk_reward_ratio < self.min_risk_reward_ratio:
                logger.info(f"İşlem reddedildi: Yetersiz R:R oranı ({risk_reward_ratio:.2f} < {self.min_risk_reward_ratio})")
                return False, stop_loss, take_profit

            return True, stop_loss, take_profit

        except Exception as e:
            logger.error(f"calculate_trade_parameters sırasında hata: {str(e)}")
            return False, 0.0, 0.0

    def evaluate_dynamic_exit(self, symbol: str, current_price: float, entry_price: float,
                              current_sl: float, current_tp: float, entry_time: str,
                              atr_value: float, lot_size: float, direction: str = "LONG"):
        """
        Fiyat lehimize veya yatayda gittiğinde tetiklenen,
        Breakeven, Trailing Stop, Scale-Out ve Time-Stop kurallarını barındıran gelişmiş çıkış motoru.

        Args:
            current_sl (float): Veritabanındaki güncel Stop Loss
            entry_time (str): İşleme giriş zamanı (ISO format)

        Returns:
            dict: {
                'action': 'HOLD' | 'UPDATE_SL' | 'PARTIAL_CLOSE' | 'FULL_CLOSE_TIMEOUT',
                'new_sl': float,
                'message': str,
                'close_ratio': float (0.0 to 1.0)
            }
        """
        result = {
            'action': 'HOLD',
            'new_sl': current_sl,
            'message': "",
            'close_ratio': 0.0
        }

        try:
            if direction == "LONG":
                # 1. TIME-STOP (Zaman Aşımı) Kuralı
                # Bir hisse senedi alındıktan sonra 10 iş günü geçmesine rağmen ne kâr hedefine ne de
                # stop seviyesine ulaşmıyor, yatayda sürünüyorsa, bu bir fırsat maliyetidir (Opportunity Cost).
                if entry_time:
                    entry_date = datetime.fromisoformat(entry_time)
                    days_held = (datetime.now() - entry_date).days
                    if days_held >= self.max_holding_period_days:
                        result['action'] = 'FULL_CLOSE_TIMEOUT'
                        result['message'] = f"⏳ Zaman Aşımı (Time-Stop): {symbol} momentum kaybetti. Sermayeyi serbest bırakmak için pozisyonu anlık fiyattan ({current_price:.2f}) kapatın."
                        result['close_ratio'] = 1.0
                        return result

                # 2. BREAKEVEN (Başabaş) Kuralı
                # Fiyat, giriş noktasından 1 R (1 ATR) yukarı gittiğinde, riski sıfırla.
                if current_price >= entry_price + (1.0 * atr_value) and current_sl < entry_price:
                    result['action'] = 'UPDATE_SL'
                    result['new_sl'] = entry_price
                    result['message'] = f"🔒 Risk Sıfırlandı: {symbol} Stop-Loss seviyesini maliyet fiyatına (Breakeven) çekin."

                # 3. KADEMELİ KÂR ALIMI (Scale-Out)
                # Fiyat TP1 (Örn: 2 R) seviyesine ulaştığında pozisyonun yarısını kapat.
                tp1_level = entry_price + (2.0 * atr_value)
                if current_price >= tp1_level and current_price < current_tp:
                    # Not: Normalde DB'de "scale_out_done" flag'i tutulmalı.
                    # Simülasyon için aksiyonu dönüyoruz.
                    result['action'] = 'PARTIAL_CLOSE'
                    result['message'] = f"💸 Kısmi Kâr Alımı: {symbol} pozisyonunun %50'sini ({lot_size/2:.2f} Lot) kapatın. Kalan %50 için İzleyen Stop devrede."
                    result['close_ratio'] = 0.5

                    # Kısmi kâr sonrası Stop-Loss'u son tepenin 1.5 ATR altına çek (Trailing)
                    trailing_level = current_price - (1.5 * atr_value)
                    if trailing_level > result['new_sl']:
                        result['new_sl'] = trailing_level

                # 4. ATR TRAILING (İzleyen Stop) Kuralı
                # Fiyat lehimize gitmeye devam ettikçe Stop-Loss sürekli yukarı çekilir. (Asla aşağı inmez)
                trailing_level = current_price - (2.0 * atr_value)
                if trailing_level > result['new_sl']:
                    result['action'] = 'UPDATE_SL'
                    result['new_sl'] = trailing_level
                    # Breakeven mesajını ezmemesi için kontrol
                    if not result['message']:
                         result['message'] = f"🛡️ İzleyen Stop (Trailing Stop) Güncellendi: {symbol} Yeni Stop-Loss {result['new_sl']:.2f}"

            return result

        except Exception as e:
            logger.error(f"Dinamik Çıkış (Dynamic Exit) değerlendirmesinde hata: {str(e)}")
            return result

    def calculate_position_size(self, current_balance: float, entry_price: float, stop_loss: float) -> float:
         if current_balance <= 0 or entry_price <= 0:
             logger.warning("Bakiye veya giriş fiyatı 0 veya negatif.")
             return 0.0
         if stop_loss >= entry_price:
             logger.warning("Stop Loss giriş fiyatına eşit veya ondan büyük olamaz (LONG işlem).")
             return 0.0

         risk_per_share = entry_price - stop_loss
         max_risk_amount = current_balance * 0.02
         shares_to_buy = max_risk_amount / risk_per_share
         max_shares_possible = current_balance / entry_price

         final_shares = min(shares_to_buy, max_shares_possible)
         return max(0.0, final_shares)

    """
    [QUANT MİMARI NOTU - SERMAYE ROTASYONU VE FIRSAT MALİYETİ]
    Amatör yatırımcılar sadece "nereden gireceğine" odaklanır. Kurumsal yapı ise
    "içerideyken ne yapılacağına" ve "ne zaman çıkılacağına" kafa yorar.
    İşleme girdikten sonra fiyat yataya sarıp günlerce hareket etmezse, paranız
    "ölü bir varlıkta" kilitlenir. Buna finans terminolojisinde Fırsat Maliyeti denir.

    Time-Stop (Zaman Aşımı), pozisyon kârda veya zararda olsun fark etmeksizin
    beklenen ivme (momentum) gerçekleşmediği için sermayeyi serbest bırakıp
    yeni doğan fırsatlara (Capital Rotation) aktarmanızı sağlar. "Cut your losses
    short, let your winners run" kuralı, Scale-Out ve Trailing Stop ile ete
    kemiğe bürünür.
    """
