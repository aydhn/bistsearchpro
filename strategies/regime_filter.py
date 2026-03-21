import logging

logger = logging.getLogger(__name__)

class RegimeFilter:
    """
    Yatay (Range) piyasalarda testere (whipsaw) hareketlerinden kaçınmak için
    tasarlanmış ADX ve EMA200 tabanlı rejim filtresi.
    """

    @staticmethod
    def determine_regime(df_ind):
        """
        Gelen DataFrame üzerinden son barlara bakarak güncel piyasa rejimini tayin eder.

        Kural Seti:
        Eğer ADX > 25 ise sistem REGIME_TREND durumuna geçer.
        Eğer ADX < 25 ise sistem REGIME_RANGE (Yatay) durumuna geçer.

        Yön Tayini:
        Mevcut kapanış fiyatı EMA(200)'ün üzerindeyse yönü BULL,
        altındaysa BEAR olarak etiketler.
        """
        if df_ind is None or df_ind.empty:
            logger.warning("Empty DataFrame provided to regime filter.")
            return None

        # pandas-ta calculates ADX, but we might not have added it in Faz 9 yet.
        # Let's add it dynamically if missing or just require it.
        if 'ADX_14' not in df_ind.columns:
            # We must calculate ADX if it's not present.
            # Doing it inline to keep it vectorized and simple.
            df_ind.ta.adx(length=14, append=True)

        try:
            # Get the latest row (most recent bar)
            latest = df_ind.iloc[-1]

            # 1. Rejim Tespiti (Trend veya Yatay)
            adx_val = latest.get('ADX_14', 0)

            if adx_val > 25:
                regime = "REGIME_TREND"
            else:
                regime = "REGIME_RANGE"

            # 2. Yön Tespiti (BULL veya BEAR)
            close_price = latest['close']

            # Using EMA200 from our pipeline
            ema200_val = latest.get('EMA_200') or latest.get('ema_200', 0)

            if close_price > ema200_val:
                direction = "BULL"
            else:
                direction = "BEAR"

            logger.debug(f"Piyasa Rejimi Tayini: {regime}, Yön: {direction} (ADX={adx_val:.2f}, Fiyat={close_price}, EMA200={ema200_val:.2f})")

            return {
                "regime": regime,
                "direction": direction,
                "adx_value": adx_val
            }

        except KeyError as e:
            logger.error(f"Missing column required for regime filter: {e}")
            return None
        except Exception as e:
            logger.error(f"Regime filter error: {e}")
            return None
