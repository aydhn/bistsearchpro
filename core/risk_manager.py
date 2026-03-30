import json
import logging
from core.logger_engine import LoggerEngine
from config.config_manager import ConfigManager
from core.universe import Universe

# Risk yönetim katmanımız, "Confluence" mantığıyla çalışan strateji motorunun kararlarını,
# sermayeyi korumak ve matematiksel avantajı (Edge) maksimize etmek için onaylar veya VETO eder.
# Sabit kesir risk modeli, dinamik lot hesaplaması ve çeşitlendirme kurallarını içerir.

logger = LoggerEngine.get_trade_logger()

class RiskManager:
    @staticmethod
    def calculate_position_size(current_balance, entry_price, stop_loss):
        if stop_loss >= entry_price or entry_price <= 0 or current_balance <= 0:
            logger.warning("RiskManager: Geçersiz giriş fiyatı, stop_loss veya kasa bakiyesi! VETO (Hata).")
            return 0

        risk_percent = float(ConfigManager.get("trading_parameters", "MAX_RISK_PER_TRADE_PERCENT") or 2.0)
        risk_amount = current_balance * (risk_percent / 100.0)
        risk_per_share = entry_price - stop_loss

        lot_size = risk_amount / risk_per_share
        return int(lot_size)

    @staticmethod
    def vet_signal(symbol, signal_data, portfolio_manager):
        """AL/SAT sinyallerini onaylar veya VETO eder."""
        if signal_data["signal"] != 1:
            return False, "Sinyal Yok veya SAT"

        # VETO 1: Maksimum Açık Pozisyon Sınırı
        max_positions = int(ConfigManager.get("trading_parameters", "MAX_OPEN_POSITIONS") or 8)
        open_positions = portfolio_manager.get_open_positions()

        if len(open_positions) >= max_positions:
            logger.warning(f"RiskManager: Maksimum açık pozisyon sınırına ({max_positions}) ulaşıldı. VETO!")
            return False, "Maksimum Pozisyon Sınırı"

        # VETO 2: Aynı Hissede Çift İşlem Yasağı (Pyramiding İptali)
        if any(pos["symbol"] == symbol for pos in open_positions):
            logger.warning(f"RiskManager: Zaten portföyde olan hisse ({symbol}) için yeni işlem yapılamaz. VETO!")
            return False, "Pyramiding Yasağı"

        # VETO 3: Sektör Limiti (Konsantrasyon Filtresi)
        max_per_sector = int(ConfigManager.get("trading_parameters", "MAX_POSITIONS_PER_SECTOR") or 2)
        new_sector = Universe.get_sector(symbol)

        sector_count = sum(1 for pos in open_positions if Universe.get_sector(pos["symbol"]) == new_sector)
        if sector_count >= max_per_sector:
            logger.warning(f"RiskManager: Aynı sektörden ({new_sector}) {max_per_sector} veya daha fazla hisse var. VETO!")
            return False, "Sektörel Limit Aşımı"

        # VETO 4: Bekleme Süresi (Cool-off Period) ve İntikam İşlemi Koruması
        if portfolio_manager.is_in_cooloff_period(symbol):
            logger.warning(f"RiskManager: {symbol} için bekleme süresi dolmadı. İntikam işlemi koruması devrede. VETO!")
            return False, "İntikam İşlemi Yasağı"

        # VETO 5: Kara Liste (Dynamic Blacklist) Kontrolü
        if portfolio_manager.is_blacklisted(symbol):
            logger.warning(f"RiskManager: {symbol} kara listede (Win-Rate < %30). VETO!")
            return False, "Kara Liste İhlali"

        # Risk/Ödül Oranı (Risk/Reward - R/R) Kontrolü:
        entry_price = signal_data["close"]
        atr = signal_data["atr"]
        atr_sl_mult = float(ConfigManager.get("strategy_settings", "ATR_MULTIPLIER_SL") or 1.5)
        atr_tp_mult = float(ConfigManager.get("strategy_settings", "ATR_MULTIPLIER_TP") or 3.0)

        stop_loss = entry_price - (atr_sl_mult * atr)
        take_profit = entry_price + (atr_tp_mult * atr)

        risk = entry_price - stop_loss
        reward = take_profit - entry_price

        # Eğer ATR o an çok açıksa (aşırı volatilite - spagetti mumlar) Veto et
        if (reward / risk) < 2.0:
            logger.warning(f"RiskManager: Risk/Ödül oranı ({reward/risk:.2f}) çok düşük (Min: 2.0). VETO!")
            return False, "Düşük R/R"

        # Dinamik Lot Hesaplaması
        current_balance = portfolio_manager.get_balance()
        lot_size = RiskManager.calculate_position_size(current_balance, entry_price, stop_loss)

        if lot_size <= 0:
            logger.warning("RiskManager: Yetersiz bakiye veya geçersiz risk hesaplaması. VETO!")
            return False, "Geçersiz Lot"

        # Onaylı İşlem Planı
        plan = {
            "symbol": symbol,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "lot_size": lot_size,
            "cost": lot_size * entry_price,
            "risk_amount": lot_size * (entry_price - stop_loss),
            "timestamp": str(signal_data["timestamp"])
        }

        logger.info(f"RiskManager: ONAYLI İŞLEM PLANI: {symbol} | Giriş: {entry_price} | SL: {stop_loss} | Lot: {lot_size}")
        return True, plan
