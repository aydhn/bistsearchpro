import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, coint
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class StatArbSignal:
    symbol_buy: str
    symbol_sell: str
    z_score: float
    spread: float
    is_cointegrated: bool

class StatArbEngine:
    """
    Bill Benter / Jim Simons tarzı kantitatif istatistiksel arbitraj.
    İki varlık arasındaki eşbütünleşmeyi (cointegration) test eder,
    doğrusal regresyon (linear regression) ile spread serisi çıkarır
    ve ADF testiyle durağanlığını sınar. Z-Skor ile işlem sinyali üretir.
    """

    @staticmethod
    def calculate_stat_arb(df_y, df_x, symbol_y, symbol_x):
        """
        İki hisse senedi fiyat serisi arasındaki eşbütünleşme ve z-score hesaplar.
        y: bağımlı değişken, x: bağımsız değişken.
        Dönen sonuç: StatArbSignal veya None
        """
        # Verilerin uzunlukları eşleşmeli, indekse göre hizala
        common_index = df_y.index.intersection(df_x.index)
        if len(common_index) < 100:
             logger.warning(f"Yetersiz eşleşen veri noktası: {len(common_index)}")
             return None

        y_close = df_y.loc[common_index, 'close']
        x_close = df_x.loc[common_index, 'close']

        try:
            # 1. Engle-Granger Eşbütünleşme Testi
            score, pvalue, _ = coint(y_close, x_close)

            # %5 anlamlılık düzeyinde eşbütünleşme kontrolü (p-value < 0.05)
            is_coint = pvalue < 0.05

            if not is_coint:
                logger.debug(f"{symbol_y} ve {symbol_x} arasında eşbütünleşme bulunamadı (p-value={pvalue:.4f})")
                return None

            logger.info(f"{symbol_y} ve {symbol_x} güçlü eşbütünleşik (p-value={pvalue:.4f})")

            # 2. Doğrusal Regresyon (Linear Regression) Modeli
            x_with_constant = sm.add_constant(x_close)
            model = sm.OLS(y_close, x_with_constant).fit()

            hedge_ratio = model.params['close'] # x'in katsayısı
            intercept = model.params['const'] # Sabit

            # 3. Artık (Residual/Spread) Serisini Çıkarma
            # Spread = Y - (Hedge_Ratio * X + Intercept)
            spread = y_close - (hedge_ratio * x_close + intercept)

            # 4. Spread Serisi Augmented Dickey-Fuller (ADF) Testi (Durağanlık kontrolü)
            adf_result = adfuller(spread)
            if adf_result[1] > 0.05: # Spread durağan değilse iptal
                logger.debug(f"Spread serisi ADF testini geçemedi (durağan değil). P-value: {adf_result[1]:.4f}")
                return None

            # 5. Z-Skoru Hesaplama
            mean_spread = np.mean(spread)
            std_spread = np.std(spread)

            if std_spread == 0:
                 return None

            current_spread = spread.iloc[-1]
            z_score = (current_spread - mean_spread) / std_spread

            # Sinyal Mantığı:
            # Z-Skor > +2.0 olduğunda y satılır, x alınır. (Pahalıyı sat / ucuzu al)
            # Z-Skor < -2.0 olduğunda y alınır, x satılır.

            signal_buy = None
            signal_sell = None

            if z_score > 2.0:
                signal_sell = symbol_y
                signal_buy = symbol_x
                logger.info(f"StatArb Sinyali: Z-Score={z_score:.2f} (> +2.0). {symbol_y} SAT, {symbol_x} AL.")
            elif z_score < -2.0:
                signal_buy = symbol_y
                signal_sell = symbol_x
                logger.info(f"StatArb Sinyali: Z-Score={z_score:.2f} (< -2.0). {symbol_y} AL, {symbol_x} SAT.")

            if signal_buy and signal_sell:
                 return StatArbSignal(
                     symbol_buy=signal_buy,
                     symbol_sell=signal_sell,
                     z_score=z_score,
                     spread=current_spread,
                     is_cointegrated=True
                 )
            return None

        except Exception as e:
            logger.error(f"StatArb hesaplama hatası: {e}")
            return None
