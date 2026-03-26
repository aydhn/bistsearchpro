import logging
import pandas as pd
import numpy as np
import statsmodels.api as sm

logger = logging.getLogger(__name__)

class PairsTradingStrategy:
    """
    Z-Skoru ve Göreceli Değer (Relative Value) Stratejisi.
    Eşbütünleşik (Cointegrated) bir hisse çifti arasındaki anlık fiyat
    makasının (Spread) tarihsel ortalamasından ne kadar standart sapma (Z-Skoru)
    uzaklaştığını hesaplayarak "Göreceli Ucuz" olan hisse için AL sinyali üretir.
    (BİST'te açığa satış/shortlama yapmadığımızı varsayarak sadece Uzun Yönlü
    (Long-Only) işlem fırsatlarını arar).
    """

    @staticmethod
    def generate_signal(pair: tuple, df_a: pd.DataFrame, df_b: pd.DataFrame):
        """
        Gelen iki eşbütünleşik hissenin (A ve B) DataFrame'leri üzerinden Z-Skoru hesaplar.

        Args:
            pair (tuple): ('THYAO.IS', 'PGSUS.IS')
            df_a (pd.DataFrame): THYAO son kapanışları
            df_b (pd.DataFrame): PGSUS son kapanışları

        Returns:
            dict | None: Sinyal varsa sözlük döndürür, yoksa None.
        """
        symbol_a, symbol_b = pair

        if df_a is None or df_b is None or df_a.empty or df_b.empty:
            logger.warning(f"Pairs Strategy için boş veri geldi ({symbol_a} - {symbol_b})")
            return None

        try:
            # Sadece 'close' fiyatlarını al ve aynı indekslerde birleştir
            # Fiyat serilerinin uzunluklarının ve zaman damgalarının aynı olduğundan emin ol
            df = pd.DataFrame({
                'A': df_a['close'],
                'B': df_b['close']
            }).dropna()

            if len(df) < 30: # Z-Skoru ve Hareketli Ortalama için min 30 bar gerekir
                 return None

            # 1. Hedge Oranı (Hedge Ratio - OLS Regresyon katsayısı) hesapla
            # Fiyat_A = Beta * Fiyat_B + Alpha -> Burada Beta hedge oranıdır.
            # Statsmodels ile Ordinary Least Squares (OLS) regresyonu:

            # X değişkenine sabit (constant/intercept) ekle
            X = sm.add_constant(df['B'])
            Y = df['A']

            model = sm.OLS(Y, X).fit()
            hedge_ratio = model.params['B']

            # 2. Spread (Makas) Formülü: Spread = FiyatA - (HedgeOranı * FiyatB)
            # Logaritmik (ln) fiyatlar da kullanılabilir, burada fiyat serisini koruyoruz:
            # Spread_t = ln(FiyatA_t) - n * ln(FiyatB_t) -> Prompt'ta logaritmik istendi.

            # Logaritmik yaklaşımla OLS:
            log_a = np.log(df['A'])
            log_b = np.log(df['B'])
            log_X = sm.add_constant(log_b)
            log_model = sm.OLS(log_a, log_X).fit()
            log_hedge_ratio = log_model.params['B']

            # Log Spread hesaplama
            spread = log_a - (log_hedge_ratio * log_b)

            # 3. Z-Skoru Hesaplama (Hareketli ortalama ve sapma üzerinden)
            # Z_t = (Spread_t - Mean) / StdDev
            window = 20 # 20 Günlük hareketli ortalama ve sapma
            spread_mean = spread.rolling(window=window).mean()
            spread_std = spread.rolling(window=window).std()

            z_score = (spread - spread_mean) / spread_std

            # Anlık değerleri al
            current_z = z_score.iloc[-1]
            current_price_a = df['A'].iloc[-1]
            current_price_b = df['B'].iloc[-1]

            logger.debug(f"Pairs Trading ({symbol_a}-{symbol_b}): Anlık Z-Skoru = {current_z:.2f}")

            # 4. Sinyal Kuralı (Long-Only Pairs)
            # Z-Skoru < -2.0 ise: Spread tarihsel olarak aşırı daralmış/negatife sapmıştır.
            # Bu, A hissesinin B'ye kıyasla İSTATİSTİKSEL OLARAK AŞIRI UCUZLADIĞI anlamına gelir.
            # Normalde: A'yı Al, B'yi Sat (Short) yapılır.
            # Bizim BİST modelinde: B'yi boşver, sadece ucuz kalan A hissesi için "AL" sinyali üret.
            # (Makas kapanıp Z_t sıfıra yaklaştığında kar alacağız).

            if current_z < -2.0:
                logger.info(f"⚖️ İSTATİSTİKSEL ARBİTRAJ FIRSATI ONAYLANDI: {symbol_a} ({symbol_b}'ye göre) aşırı iskontolu! (Z-Score: {current_z:.2f})")

                # Bu stratejinin Telegram raporu standart stratejilerden farklı olacak.
                # 'is_stat_arb' bayrağı (flag) ile raporlayıcıyı uyaracağız.
                return {
                    "direction": "BUY",
                    "confidence": 90.0, # Güven skorunu yüksek tut, çünkü istatistiksel bir edge var.
                    "source": "Statistical_Arbitrage",
                    "is_stat_arb": True,
                    "pair": (symbol_a, symbol_b),
                    "z_score": current_z,
                    "hedge_ratio": log_hedge_ratio
                }

            # Eğer Z-Skoru > +2.0 ise: A aşırı pahalı, B aşırı ucuzdur. B'yi Al!
            elif current_z > 2.0:
                 logger.info(f"⚖️ İSTATİSTİKSEL ARBİTRAJ FIRSATI ONAYLANDI: {symbol_b} ({symbol_a}'ya göre) aşırı iskontolu! (Z-Score: {current_z:.2f})")
                 return {
                    "direction": "BUY",
                    "confidence": 90.0,
                    "source": "Statistical_Arbitrage",
                    "is_stat_arb": True,
                    "pair": (symbol_b, symbol_a), # B'yi alacağımız için pair'i ters çevirip yolluyoruz
                    "z_score": current_z,
                    "hedge_ratio": log_hedge_ratio
                }

            return None

        except Exception as e:
            logger.error(f"Pairs Trading Z-Skoru hesaplama hatası ({symbol_a}-{symbol_b}): {e}")
            return None
