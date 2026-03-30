import pandas_ta as ta
import pandas as pd
import numpy as np
from config.config_manager import ConfigManager

# Teknik ve istatistiksel analiz motorunu yazıyoruz.
# Hesaplamaların yavaş "for" döngüleriyle değil, kesinlikle vektörel işlemlerle (Pandas/NumPy)
# veya optimize edilmiş pandas_ta kütüphanesiyle yapılması ŞARTTIR.

class IndicatorEngine:
    @staticmethod
    def enrich_data(df: pd.DataFrame) -> pd.DataFrame:
        """Ham DataFrame'i alır, teknik ve istatistiksel sinyallerle doldurur."""
        if df is None or df.empty:
            return df

        ema_short = int(ConfigManager.get("strategy_settings", "EMA_SHORT") or 50)
        ema_long = int(ConfigManager.get("strategy_settings", "EMA_LONG") or 200)
        vol_sma_period = int(ConfigManager.get("strategy_settings", "VOLUME_SMA_PERIOD") or 20)

        # 1. Trend ve Momentum
        df['EMA_short'] = ta.ema(df['close'], length=ema_short)
        df['EMA_long'] = ta.ema(df['close'], length=ema_long)

        # MACD: Sinyal çizgisini yukarı kesiyorsa tetikleyici olarak kullanılacak.
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        if macd is not None and not macd.empty:
            df['MACD'] = macd['MACD_12_26_9']
            df['MACD_signal'] = macd['MACDs_12_26_9']
            df['MACD_hist'] = macd['MACDh_12_26_9']

        # RSI: Aşırı satım/alım
        df['RSI'] = ta.rsi(df['close'], length=14)

        # 2. Volatilite ve Risk Metrikleri (JP Morgan vizyonu)
        # ATR: Dinamik stop-loss ve pozisyon büyüklüğü hesaplamak için ileride hayati olacak.
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        # Bollinger Bantları
        bbands = ta.bbands(df['close'], length=20, std=2)
        if bbands is not None and not bbands.empty:
            df['BBL_20_2.0'] = bbands['BBL_20_2.0']
            df['BBM_20_2.0'] = bbands['BBM_20_2.0']
            df['BBU_20_2.0'] = bbands['BBU_20_2.0']

        # 3. İstatistiksel Derinlik
        # VWAP (Hacim Ağırlıklı Ortalama Fiyat)
        df['VWAP'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])

        # Hacim Ortalama
        df['Volume_SMA'] = ta.sma(df['volume'], length=vol_sma_period)

        # Z-Skoru (Mean Reversion stratejileri için)
        df['Z_Score'] = (df['close'] - ta.sma(df['close'], length=20)) / ta.stdev(df['close'], length=20)

        # Tavan/Taban Algılaması ("Locked Limit") BIST Marjı: %10
        # Likidite olmadığı için teknik analiz anlamsızlaşır.
        pct_change = df['close'].pct_change() * 100
        df['Locked_Limit'] = np.where((pct_change >= 9.8) | (pct_change <= -9.8), True, False)

        # Dinamik Volatilite Filtresi (ATR Spike Detection)
        # ATR > 3x ortalama ATR ise "Volatilite Şoku" olarak algıla.
        df['ATR_SMA_50'] = ta.sma(df['ATR'], length=50)
        df['ATR_Spike'] = np.where(df['ATR'] > (df['ATR_SMA_50'] * 3), True, False)

        df.dropna(inplace=True)
        return df
