import pandas as pd
from core.logger_engine import LoggerEngine
from config.config_manager import ConfigManager

logger = LoggerEngine.get_trade_logger()

# Strateji modülü, `indicators.py` tarafından zenginleştirilmiş DataFrame'i alıp her bir bar/mum için sinyal üretecek.
# Tek bir indikatöre güvenmeyip; "Confluence" (Çoklu Doğrulama) mimarisi kullanıyoruz.
# Çıktısı kesin ve net olmalıdır: `1` (AL), `-1` (SAT) veya `0` (BEKLE).

class CoreStrategy:
    @staticmethod
    def generate_signal(df: pd.DataFrame, symbol: str) -> dict:
        if df is None or df.empty or len(df) < 2:
            return {"signal": 0, "reason": "Yetersiz Veri"}

        current_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        # Tavan/Taban Koruması (Locked Limit) veya Volatilite Şoku varsa
        # diğer indikatörler ne derse desin, o bar için KESİNLİKLE "0" (BEKLE) sinyali üret, sahte AL/SAT blokla.
        if current_row.get("Locked_Limit", False):
            return {"signal": 0, "reason": "Tavan/Taban Durumu"}

        if current_row.get("ATR_Spike", False):
            return {"signal": 0, "reason": "Volatilite Şoku (ATR Spike)"}

        # Trend Filtresi (EMA 200)
        close = current_row["close"]
        ema_long = current_row["EMA_long"]
        ema_short = current_row["EMA_short"]

        # Momentum Doğrulaması (RSI ve MACD Kesişimi)
        rsi = current_row["RSI"]
        prev_rsi = prev_row["RSI"]
        rsi_oversold = float(ConfigManager.get("strategy_settings", "RSI_OVERSOLD") or 30)

        macd = current_row.get("MACD", 0)
        macd_signal = current_row.get("MACD_signal", 0)
        prev_macd = prev_row.get("MACD", 0)
        prev_macd_signal = prev_row.get("MACD_signal", 0)

        # Risk/Volatilite Filtresi (Hacim ve Bollinger)
        volume = current_row["volume"]
        vol_sma = current_row.get("Volume_SMA", 0)

        bbl = current_row.get("BBL_20_2.0", 0)

        signal = 0
        reason = "Bekle"

        # Confluence Mantığı: False positive oranını düşürmek için
        # üç filtrenin de aynı anda AL demesini bekliyoruz.
        is_uptrend = close > ema_long
        is_rsi_crossover = (prev_rsi <= rsi_oversold) and (rsi > rsi_oversold)
        is_macd_crossover = (prev_macd <= prev_macd_signal) and (macd > macd_signal)
        is_volume_high = volume > vol_sma
        is_bb_bounce = close > bbl and prev_row["close"] <= prev_row.get("BBL_20_2.0", 0)

        # Ana Yön AL
        if is_uptrend and (is_rsi_crossover or is_macd_crossover) and (is_volume_high or is_bb_bounce):
            signal = 1
            reason = "Fiyat EMA200 üzerinde, MACD/RSI kesişimi onaylandı ve Hacim/BB destekliyor."
            logger.info(f"SİNYAL UYARISI: {symbol} Yön: AL 🟢 Gerekçe: {reason}")

        # Ana Yön SAT
        elif close < ema_long and rsi > float(ConfigManager.get("strategy_settings", "RSI_OVERBOUGHT") or 70):
             # Yüksek Win-rate hedeflediğimiz için short aramayı kısıtlıyor ve genelde çıkış kuralı (Risk-Off) uyguluyoruz.
             # Sistem long biaslıdır, ancak short stratejisi de esnek şekilde eklenebilir.
             signal = -1
             reason = "Fiyat EMA200 altında ve RSI Aşırı Alım."

        return {
            "signal": signal,
            "reason": reason,
            "close": close,
            "atr": current_row["ATR"],
            "timestamp": df.index[-1]
        }
