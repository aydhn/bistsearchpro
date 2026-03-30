import yfinance as yf
from config.config_manager import ConfigManager
from core.logger_engine import LoggerEngine
import pandas as pd
import numpy as np
import pandas_ta as ta

logger = LoggerEngine.get_system_logger()

# "Risk-On / Risk-Off" (Risk Alınabilir / Riskten Kaçın) şalteri.
# BIST100 (XU100) endeksi sert bir düşüş trendindeyken yeni uzun (Long) pozisyonlar açmak intihardır.
# Bu modül, tarama döngüsü başlamadan önce `True` (Risk-On) veya `False` (Risk-Off) döndürmelidir.

class MarketFilter:
    @staticmethod
    def get_market_regime():
        try:
            # XU100 verisini çek
            df = yf.download("XU100.IS", period="1y", interval="1d", progress=False, show_errors=False)

            if df is None or df.empty:
                logger.warning("MarketFilter: XU100 verisi çekilemedi. GÜVENLİK AMACIYLA DURDURULDU.")
                return False, "Veri Alınamadı"

            df.columns = df.columns.droplevel(1) if isinstance(df.columns, pd.MultiIndex) else df.columns
            df = df.rename(columns={'Close': 'close'})
            df.ffill(inplace=True)
            df.bfill(inplace=True)

            close = df['close'].iloc[-1]
            ema_200 = ta.ema(df['close'], length=200).iloc[-1]
            ema_50 = ta.ema(df['close'], length=50).iloc[-1]
            pct_change = df['close'].pct_change().iloc[-1] * 100

            # Kural 1: XU100 anlık fiyatı, kendi EMA(50)'sinin altındaysa piyasa ayıdır (Bear Market).
            if close < ema_50:
                logger.info(f"Market Regime: RISK-OFF 🔴 (Endeks EMA50 altında)")
                return False, "EMA(50) Altında"

            # Kural 2: XU100 günlük değişimi % -2.5 ve üzerindeyse (ani çöküş/panik) piyasa toksiktir.
            if pct_change <= -2.5 and pct_change > -4.8:
                logger.info(f"Market Regime: RISK-OFF 🔴 (Sert Günlük Kayıp: {pct_change:.2f}%)")
                return False, f"Sert Günlük Kayıp: {pct_change:.2f}%"

            # Makro Devre Kesici Algılaması (Circuit Breaker Koruması):
            if pct_change <= -4.8:
                logger.error(f"⚠️ ACİL DURUM PROTOKOLÜ: XU100 %5 devre kesici sınırında ({pct_change:.2f}%)")
                return False, "DEVRE KESİCİ SINIRI"

            return True, "Risk-On 🟢"

        except Exception as e:
            logger.error(f"MarketFilter Hatası: {e}")
            return False, "Motor Hatası"
