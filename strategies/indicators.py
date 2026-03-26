import pandas_ta as ta
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """
    Pandas-ta kütüphanesini kullanarak vektörel ve optimize indikatör hesaplamaları yapar.
    Sıfır bütçe ve donanım dostu (döngüsüz) prensiplere uyar.
    Memory leak önlemek için DataFrame manipülasyonları inplace veya kontrollü yapılır.
    """

    @staticmethod
    def calculate_all(df: pd.DataFrame, limit: int = None) -> pd.DataFrame:
        """
        Gelen ham DataFrame'in son N mumu (limit) üzerinde tüm teknik indikatörleri
        hesaplar ve aynı DataFrame'e ekler.
        """
        if df is None or df.empty:
            logger.warning("calculate_all için boş DataFrame sağlandı.")
            return df

        # Eğer limit belirtilmişse, gereksiz hesaplamaları önlemek için df'i kes
        if limit and len(df) > limit:
            df = df.tail(limit).copy()

        # Pandas-ta Strategy yapısı ile toplu vektörel hesaplama
        try:
            # 1. Trend ve İvme: EMA (20, 50) ve RSI (14)
            # 2. Volatilite: ATR (14) - Dinamik stop-loss için
            # 3. İstatistiksel Sapma: Bollinger Bantları (20, 2)

            # Sütun isimlendirme çakışmalarını önlemek için prefix vs kullanılabilir
            # veya pandas-ta'nın standart isimlendirmeleri kabul edilebilir.

            # Vektörel hesaplamalar
            df.ta.ema(length=20, append=True)
            df.ta.ema(length=50, append=True)
            df.ta.rsi(length=14, append=True)
            df.ta.atr(length=14, append=True)
            df.ta.bbands(length=20, std=2, append=True)

            # ADX (Trend Following stratejisi için)
            df.ta.adx(length=14, append=True)

            # MACD (Trend Following stratejisi için)
            df.ta.macd(fast=12, slow=26, signal=9, append=True)

            # Donchian Channels (Volatility Breakout stratejisi için)
            df.ta.donchian(lower_length=20, upper_length=20, append=True)

            # Sütun isimlerini kolay kullanım için standartlaştır
            # pandas_ta sütun isimleri örn: 'EMA_20', 'RSI_14', 'ATRr_14', 'BBL_20_2.0', 'BBM_20_2.0', 'BBU_20_2.0'
            rename_map = {
                'EMA_20': 'ema_20',
                'EMA_50': 'ema_50',
                'RSI_14': 'rsi',
                'ATRr_14': 'atr',
                'BBL_20_2.0': 'bb_lower',
                'BBM_20_2.0': 'bb_mid',
                'BBU_20_2.0': 'bb_upper',
                'ADX_14': 'adx',
                'MACD_12_26_9': 'macd',
                'MACDs_12_26_9': 'macd_signal',
                'DCL_20_20': 'donchian_lower',
                'DCU_20_20': 'donchian_upper'
            }

            # Yalnızca var olan sütunları yeniden adlandır (hata almamak için)
            actual_rename = {k: v for k, v in rename_map.items() if k in df.columns}
            df.rename(columns=actual_rename, inplace=True)

            # Na olan ilk satırları temizle
            df.dropna(inplace=True)

            return df

        except Exception as e:
            logger.error(f"İndikatör hesaplamasında hata: {str(e)}")
            return df
