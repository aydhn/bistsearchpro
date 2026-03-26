import logging

logger = logging.getLogger(__name__)

class RegimeFilter:
    """
    BIST 100 endeksinin (XU100.IS) genel sağlığını ölçecek bağımsız sınıf.
    Makro Trend Kuralı: XU100, 200 günlük Basit Hareketli Ortalamanın (SMA 200) altındaysa
    piyasa "Ayı (Bear)", üstündeyse "Boğa (Bull)" rejimi olarak etiketlenir.

    Eğer piyasa Ayı rejimindeyse, sistemdeki Long (AL) sinyalleri reddedilmeli
    veya Kelly lot hesaplayıcısındaki risk oranı yarı yarıya (Half-Risk) düşürülmelidir.
    """

    @staticmethod
    def determine_regime(df_xu100):
        """
        BIST 100 günlük verisi (df_xu100) üzerinden piyasa rejimini tayin eder.
        Gelen veri seti XU100.IS'in GÜNLÜK (1D) mumlarını içermelidir.
        """
        if df_xu100 is None or df_xu100.empty:
            logger.warning("Regime filter için boş DataFrame sağlandı.")
            return None

        try:
            # Eğer SMA_200 hesaplanmamışsa hesapla
            if 'sma_200' not in df_xu100.columns and 'SMA_200' not in df_xu100.columns:
                df_xu100.ta.sma(length=200, append=True)

            # Sütun ismini standartlaştır (pandas_ta varsayılanı SMA_200 olabilir)
            sma_col = 'sma_200' if 'sma_200' in df_xu100.columns else 'SMA_200'

            # Yeterli veri yoksa nötr dön
            if df_xu100[sma_col].isna().iloc[-1]:
                logger.warning("XU100 verisi 200 günden az, rejim tayin edilemedi.")
                return {"regime": "NEUTRAL", "sma200": 0.0, "close": df_xu100['close'].iloc[-1]}

            # Son mum verilerini al
            latest = df_xu100.iloc[-1]
            close_price = latest['close']
            sma200_val = latest[sma_col]

            # Rejim Tespiti
            if close_price > sma200_val:
                regime = "BULL"
            else:
                regime = "BEAR"

            logger.info(f"XU100 Piyasa Rejimi: {regime} (Fiyat={close_price:.2f}, SMA200={sma200_val:.2f})")

            return {
                "regime": regime,
                "sma200": sma200_val,
                "close": close_price
            }

        except KeyError as e:
            logger.error(f"Regime filter için gerekli sütun bulunamadı: {e}")
            return None
        except Exception as e:
            logger.error(f"Regime filter hesaplama hatası: {e}")
            return None
