import pandas as pd
import numpy as np

class StrategyEngine:
    """
    Karar mekanizması (Confluence - Çoklu Doğrulama).
    Phase 3: Yüksek win-rate için Trend, Momentum ve Risk filtrelerinin birleşimi.
    """
    def __init__(self, config):
        self.ema_short = config['strategy_settings']['EMA_SHORT']
        self.ema_long = config['strategy_settings']['EMA_LONG']
        self.rsi_oversold = config['strategy_settings']['RSI_OVERSOLD']
        self.vol_shock_mult = config['strategy_settings']['VOLATILITY_SHOCK_MULTIPLIER']

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Gelen DataFrame'i vektörel olarak analiz edip 'signal' kolonu ekler (1: AL, -1: SAT, 0: BEKLE).
        Ayrıca Volatilite Şoku ve Limit kilitlenmelerinde (Tavan/Taban) sinyali 0'a zorlar.
        """
        # Sinyal Sütununu Başlat
        df['signal'] = 0
        df['signal_reason'] = ""

        # Sütun varlık kontrolü
        req_cols = [f'ema_{self.ema_long}', 'rsi', 'macd', 'macd_signal', 'volume', 'volume_sma_20', 'locked_limit', 'atr_sma_3', f'atr_sma_{self.volatility_lookback}']
        for c in req_cols:
            if c not in df.columns:
                return df

        ema_l = f'ema_{self.ema_long}'
        atr_long = f'atr_sma_{self.volatility_lookback}'

        # --- ALIM (LONG) CONFLUENCE ---
        # 1. Trend: Fiyat > EMA(200)
        cond_trend_up = df['close'] > df[ema_l]

        # 2. Momentum: RSI aşırı satımdan dönüyor (Örn: RSI_t-1 < 30 ve RSI_t > 30)
        # Veya MACD Kesişimi: MACD > MACD_Signal ve MACD_t-1 < MACD_Signal_t-1
        cond_rsi_cross = (df['rsi'].shift(1) < self.rsi_oversold) & (df['rsi'] >= self.rsi_oversold)
        cond_macd_cross = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
        cond_momentum = cond_rsi_cross | cond_macd_cross

        # 3. Hacim Doğrulaması: İşlem hacmi, 20 barlık ortalamanın üzerinde olmalı
        cond_volume = df['volume'] > df['volume_sma_20']

        # --- ANOMALİ SAVUNMASI ---
        # Locked Limit (Tavan/Taban) değilse
        cond_not_locked = ~df['locked_limit']

        # Volatilite Şoku Değilse (Spagetti Mum Koruması)
        cond_no_vol_shock = df['atr_sma_3'] <= (df[atr_long] * self.vol_shock_mult)

        # Tüm şartları birleştir
        buy_condition = cond_trend_up & cond_momentum & cond_volume & cond_not_locked & cond_no_vol_shock

        # Sinyalleri 1 yap
        df.loc[buy_condition, 'signal'] = 1
        df.loc[buy_condition, 'signal_reason'] = f"Trend UP, Momentum Onaylı, Hacimli. Volatilite normal."

        # Not: Sadece LONG (Alım) pozisyonlu ilerliyoruz. BIST'te açığa satış genellikle bireysel yatırımcı için riskli ve zordur.

        return df
