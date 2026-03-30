import pandas as pd
import pandas_ta as ta
import numpy as np

class IndicatorEngine:
    """
    Vektörel (NumPy/Pandas_ta) indikatör ve sinyal zenginleştirme motoru.
    Kıdemli Quant Notu: Kesinlikle iterrows() veya döngü kullanılmamıştır (Performance Constraint).
    """
    def __init__(self, config):
        self.ema_short = config['strategy_settings']['EMA_SHORT']
        self.ema_long = config['strategy_settings']['EMA_LONG']
        self.rsi_period = config['strategy_settings']['RSI_PERIOD']
        self.atr_period = config['strategy_settings']['ATR_PERIOD']
        self.volatility_lookback = config['strategy_settings']['VOLATILITY_LOOKBACK']

    def enrich_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ham OHLCV verisini zenginleştirir.
        Girdi kolonları lowercase ('open', 'high', 'low', 'close', 'volume') olmalıdır.
        """
        try:
            # Trend: Kısa ve Uzun EMA
            df[f'ema_{self.ema_short}'] = ta.ema(df['close'], length=self.ema_short)
            df[f'ema_{self.ema_long}'] = ta.ema(df['close'], length=self.ema_long)

            # Momentum: RSI ve MACD
            df['rsi'] = ta.rsi(df['close'], length=self.rsi_period)
            macd_df = ta.macd(df['close'])
            if macd_df is not None and not macd_df.empty:
                # pandas_ta macd 3 kolon döner: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
                # Kolaylık için dinamik sütun ismini bulup 'macd' ve 'macd_signal' olarak atıyoruz
                macd_cols = macd_df.columns
                df['macd'] = macd_df[macd_cols[0]]
                df['macd_signal'] = macd_df[macd_cols[2]]

            # Volatilite/Risk: ATR (Average True Range)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.atr_period)

            # Bollinger Bantları (Yanlış Kırılımlar İçin)
            bbands = ta.bbands(df['close'], length=20, std=2)
            if bbands is not None and not bbands.empty:
                bb_cols = bbands.columns
                df['bb_lower'] = bbands[bb_cols[0]]
                df['bb_mid'] = bbands[bb_cols[1]]
                df['bb_upper'] = bbands[bb_cols[2]]

            # Hacim Ortalama (Sinyal Doğrulaması)
            df['volume_sma_20'] = ta.sma(df['volume'], length=20)

            # --- ANOMALİ: Volatilite Kalkanı (ATR Spike Detection) ---
            # Son 3 barın ATR ortalaması > Son 50 barın ATR ortalaması * Çarpan ise Şok var!
            df['atr_sma_3'] = ta.sma(df['atr'], length=3)
            df[f'atr_sma_{self.volatility_lookback}'] = ta.sma(df['atr'], length=self.volatility_lookback)

            # --- ANOMALİ: Tavan/Taban Algılaması (Locked Limit) ---
            # BIST marj limiti günlüktür. %9.8 ile %10 arası değişim kilitlenmeyi gösterir.
            # Vektörel değişim yüzdesi hesabı
            df['pct_change'] = df['close'].pct_change() * 100

            # Kilitlenme (Locked Limit) maskesi: Mutlak %9.8'den büyük günlük değişim
            df['locked_limit'] = np.where(df['pct_change'].abs() > 9.8, True, False)

            df.dropna(inplace=True)
            return df
        except Exception as e:
            # Hata durumunda boş dataframe döner
            print(f"İndikatör hesaplama hatası: {e}")
            return pd.DataFrame()
