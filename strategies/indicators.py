import pandas_ta as ta
import logging

logger = logging.getLogger(__name__)

class IndicatorPipeline:
    """
    Vektörel (döngüsüz) teknik indikatör hesaplayıcı.
    pandas-ta kullanarak devasa veri setlerinde bile milisaniyelerde sonuç üretir.
    """

    @staticmethod
    def add_indicators(df):
        """
        Gelen OHLCV DataFrame'ine tek bir fonksiyon çağrısıyla
        Trend, Momentum ve Volatilite indikatörlerini ekler.
        """
        if df.empty or len(df) < 200:
             logger.warning("Yetersiz veri. İndikatör hesaplanamıyor (en az 200 bar gerekli).")
             return None

        df_ind = df.copy()

        try:
            # 1. Trend İndikatörleri (EMA: Üstel Hareketli Ortalama)
            df_ind.ta.ema(length=20, append=True)
            df_ind.ta.ema(length=50, append=True)
            df_ind.ta.ema(length=200, append=True)

            # 2. Momentum İndikatörleri (RSI ve MACD)
            df_ind.ta.rsi(length=14, append=True)

            # MACD parametreleri: fast=12, slow=26, signal=9. df.ta.macd()
            # pandas-ta standart kolon isimlendirmesi: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
            df_ind.ta.macd(fast=12, slow=26, signal=9, append=True)

            # 3. Volatilite İndikatörleri (ATR ve Bollinger Bantları)
            df_ind.ta.atr(length=14, append=True)

            # Bollinger Bantları: BB_LOWER, BB_MID, BB_UPPER (standart sapma: 2, periyot: 20)
            df_ind.ta.bbands(length=20, std=2, append=True)

            # Başlangıç barlarındaki hesaplanamayan NaN değerlerini kes (trim)
            df_ind.dropna(inplace=True)

            # Rename columns for easier access (optional but recommended for consistency)
            # Default pandas-ta names might include parameters, so we can map them

            rename_map = {
                'EMA_20': 'ema_20',
                'EMA_50': 'ema_50',
                'EMA_200': 'ema_200',
                'RSI_14': 'rsi_14',
                'MACD_12_26_9': 'macd',
                'MACDh_12_26_9': 'macd_hist',
                'MACDs_12_26_9': 'macd_signal',
                'ATRr_14': 'atr_14',
                'BBL_20_2.0': 'bb_lower',
                'BBM_20_2.0': 'bb_mid',
                'BBU_20_2.0': 'bb_upper',
                'BBB_20_2.0': 'bb_bandwidth',
                'BBP_20_2.0': 'bb_percent'
            }

            df_ind.rename(columns=rename_map, inplace=True, errors='ignore')

            logger.debug(f"Indicators added successfully. Resulting shape: {df_ind.shape}")
            return df_ind

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return None
