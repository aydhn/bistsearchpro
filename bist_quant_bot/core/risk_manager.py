import logging

class RiskManager:
    """
    Sistemin kasası ve güvenlik duvarı.
    "Sabit Kesir (Fixed Fractional)" risk modeli ile her işlemde kasanın belirli bir %'sini riske atar.
    Dinamik Lot/Adet hesaplaması (Position Sizing) ATR tabanlıdır.
    """
    def __init__(self, config, portfolio):
        self.max_risk_pct = config['trading_parameters']['MAX_RISK_PER_TRADE_PCT']
        self.max_open_positions = config['trading_parameters']['MAX_OPEN_POSITIONS']
        self.atr_multiplier_sl = config['strategy_settings']['ATR_MULTIPLIER_SL']
        self.atr_multiplier_tp = config['strategy_settings']['ATR_MULTIPLIER_TP']
        self.portfolio = portfolio

    def validate_and_size_position(self, symbol: str, entry_price: float, atr_value: float) -> dict:
        """
        Bir AL sinyali geldiğinde "VETO" testinden geçirir. Onaylanırsa {lot_size, sl_price, tp_price} döner.
        Reddedilirse (VETO) None döner.
        """
        # 1. Aşırı İşlem / Çeşitlendirme Koruması (Max Positions)
        open_pos_count = len(self.portfolio.get_open_positions())
        if open_pos_count >= self.max_open_positions:
            logging.info(f"VETO [{symbol}]: Maksimum açık pozisyon limitine ulaşıldı ({self.max_open_positions}).")
            return None

        # 2. Aynı Hissede Çift İşlem Yasağı (Pyramiding İptali)
        if self.portfolio.has_open_position(symbol):
            logging.info(f"VETO [{symbol}]: Zaten portföyde var. İkinci işleme izin verilmez.")
            return None

        # 3. Bekleme Süresi (Cool-off / İntikam İşlemi Koruması)
        # portfolio modülü son kapanan işlemi tarihine göre filtreleyecek
        if self.portfolio.is_in_cooloff(symbol):
            logging.info(f"VETO [{symbol}]: Hisse bekleme (Cool-off) süresinde. İntikam işlemi engellendi.")
            return None

        # 4. Dinamik Kara Liste (Self-Correction) AnalyticsEngine Tarafından
        if self.portfolio.is_blacklisted(symbol):
             logging.info(f"VETO [{symbol}]: Hisse / Sektör Dinamik Kara Listede (Blacklist). İşlem engellendi.")
             return None

        # --- MATEMATİKSEL POZİSYON HESAPLAMASI (POSITION SIZING) ---
        current_balance = self.portfolio.get_balance()
        if current_balance <= 0:
            logging.error("Kritik Hata: Sanal Bakiye Sıfır veya Eksi!")
            return None

        risk_amount = current_balance * (self.max_risk_pct / 100.0)

        # ATR bazlı Stop-Loss Mesafesi (Risk per Share)
        stop_distance = atr_value * self.atr_multiplier_sl
        if stop_distance <= 0:
             logging.error(f"Geçersiz ATR mesafesi ({stop_distance}). İşlem iptal.")
             return None

        # KURAL: Stop Loss > Entry Price ise short demektir (BIST'te Long gidiyoruz).
        # Matematiksel kesinlik için: SL = Entry - (ATR * Multiplier)
        stop_loss_price = entry_price - stop_distance

        # Eğer SL fiyatı 0 veya eksi çıkıyorsa çok volatil demektir, veto et.
        if stop_loss_price <= 0:
            logging.info(f"VETO [{symbol}]: Stop-Loss seviyesi sıfırın altında! Aşırı volatilite.")
            return None

        # Dinamik Lot (Adet) = Riske Edilen Toplam Para / Hisse Başına Riske Edilen Para
        try:
            lot_size = int(risk_amount / stop_distance)
        except ZeroDivisionError:
            return None

        # Eğer para 1 lot almaya bile yetmiyorsa iptal
        if lot_size <= 0:
            logging.info(f"VETO [{symbol}]: Ayrılan risk ({risk_amount:.2f} TL) 1 lot almak için yetersiz.")
            return None

        # Take Profit (R/R Kontrolü) - Genelde Stop mesafesinin X katı
        take_profit_price = entry_price + (atr_value * self.atr_multiplier_tp)

        logging.info(f"ONAY [{symbol}]: {lot_size} Adet. Risk: {risk_amount:.2f} TL (Kasanın %{self.max_risk_pct}'i). R/R=1:{self.atr_multiplier_tp/self.atr_multiplier_sl:.1f}")

        return {
            "symbol": symbol,
            "entry_price": entry_price,
            "lot_size": lot_size,
            "stop_loss": stop_loss_price,
            "take_profit": take_profit_price,
            "risk_amount": risk_amount
        }
