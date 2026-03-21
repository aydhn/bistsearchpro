import logging
import math
from config.settings import config

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Sermaye korumanın kalbi olan risk boyutlandırma fonksiyonlarını içerir.
    Sabit Kesir ve Yarı-Kelly Kriteri (Half-Kelly) modellerini birleştirerek
    optimal işlem hacmini (LOT sayısı) hesaplar.
    """

    @staticmethod
    def calculate_kelly_fraction(win_rate: float, risk_reward_ratio: float) -> float:
        """
        Kelly Kriteri Formülü:
        f* = W - ((1 - W) / R)
        W = Kazanma Oranı (Win Rate, 0 ile 1 arası)
        R = Risk/Ödül Oranı (Reward/Risk)
        """
        if risk_reward_ratio <= 0:
            return 0.0

        # Tam Kelly kesri
        kelly_pct = win_rate - ((1.0 - win_rate) / risk_reward_ratio)

        # Riskleri minimize etmek için Yarı-Kelly (Half-Kelly)
        half_kelly_pct = kelly_pct / 2.0

        # Sonuç %0'ın altına düşemez, negatifse işlem yapılmamalıdır
        return max(0.0, half_kelly_pct)

    @staticmethod
    def calculate_position_size(
        current_balance: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        historical_win_rate: float = 0.55 # Varsayılan kazanma oranı
    ) -> int:
        """
        Mevcut sanal sermaye (paper_wallet bakiyesi), giriş, SL ve TP değerlerine
        göre alınması gereken LOT (hisse adedi) miktarını tam sayı olarak döndürür.
        """
        if current_balance <= 0 or entry_price <= 0:
            logger.error("Geçersiz bakiye veya giriş fiyatı.")
            return 0

        # Alım yönlü işlem için Risk ve Ödül hesaplaması
        risk_per_share = entry_price - stop_loss
        reward_per_share = take_profit - entry_price

        if risk_per_share <= 0:
            logger.warning("Stop-Loss seviyesi giriş fiyatından büyük veya eşit olamaz (Sadece LONG işlemler destekleniyor).")
            return 0

        risk_reward_ratio = reward_per_share / risk_per_share

        # 1. Sabit Kesir (Fixed Fractional) Modeli Limitleri
        # Maksimum riske edilecek tutar: Sermayenin %2'si
        max_risk_amount = current_balance * config.MAX_RISK_PER_TRADE

        # Sabit Kesir modeline göre alınabilecek maksimum lot
        max_lot_fixed = math.floor(max_risk_amount / risk_per_share)

        # 2. Yarı-Kelly Kriteri
        half_kelly_pct = RiskManager.calculate_kelly_fraction(historical_win_rate, risk_reward_ratio)

        if half_kelly_pct <= 0:
            logger.info("Kelly Kriteri negatif veya sıfır döndü. İşlem iptal edildi (Matematiksel avantaj yok).")
            return 0

        # Yarı-Kelly modeline göre tahsis edilecek sermaye miktarı
        kelly_capital_allocation = current_balance * half_kelly_pct

        # Kelly modeline göre alınabilecek lot
        lot_kelly = math.floor(kelly_capital_allocation / entry_price)

        # İki modelin en muhafazakar olanını (en düşük lot) seçerek güvenliği maksimize et
        final_lot = min(max_lot_fixed, lot_kelly)

        # Toplam işlem tutarının mevcut bakiyeyi geçmesini engelle (Garanti kontrolü)
        max_affordable_lot = math.floor(current_balance / entry_price)
        final_lot = min(final_lot, max_affordable_lot)

        logger.debug(f"Risk Analizi - Bakiye: {current_balance}, Risk/Ödül: {risk_reward_ratio:.2f}, Yarı-Kelly: %{half_kelly_pct*100:.2f}")
        logger.info(f"Pozisyon Boyutlandırma Sonucu -> Sabit Kesir İzin: {max_lot_fixed} Lot, Kelly İzin: {lot_kelly} Lot. Kesinleşen: {final_lot} Lot.")

        return final_lot
