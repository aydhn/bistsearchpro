import logging
import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import coint

logger = logging.getLogger(__name__)

class CointegrationEngine:
    """
    İstatistiksel Arbitraj ve Eşli İşlem (Pairs Trading) motoru.
    Sadece korelasyona (yön benzerliği) değil, Eşbütünleşmeye (fiyat makasının zamanla
    ortalamaya dönmesi) odaklanarak piyasa nötr (Market Neutral) bir kalkan sağlar.
    """
    def __init__(self, data_fetcher):
        self.fetcher = data_fetcher
        self.cointegrated_pairs = []

    def scan_pairs(self, symbol_list: list):
        """
        Engle-Granger testini (coint) kullanarak BIST30 içindeki hisse çiftlerini tarar.
        P-value (olasılık değeri) 0.05'in altında olan çiftleri "Eşbütünleşik Çiftler"
        olarak belirler. Bu işlem ağır (N^2 karmaşıklığında) olduğu için günde
        bir kez çalıştırılması tavsiye edilir.
        """
        logger.info(f"Eşbütünleşme Taraması (Cointegration Scan) başlatılıyor... (O(N^2) işlem, lütfen bekleyin)")
        if not symbol_list or len(symbol_list) < 2:
            logger.warning("Eşbütünleşme taraması için en az 2 hisse senedi (BIST30) gereklidir.")
            return []

        # Hisselerin son 90 veya 180 günlük verilerini çek. Eşbütünleşme uzun vade gerektirir.
        price_data = {}
        for sym in symbol_list:
            try:
                # To be efficient, this could be pulled from local cache
                df = self.fetcher.fetch_ohlcv(sym, interval="1d", n_bars=90)
                if not df.empty:
                    price_data[sym] = df['close']
            except Exception as e:
                logger.error(f"Eşbütünleşme verisi çekilemedi ({sym}): {e}")

        if len(price_data) < 2:
            return []

        try:
            df_prices = pd.DataFrame(price_data).dropna()
            symbols = list(df_prices.columns)
            n_symbols = len(symbols)

            pairs = []

            # Sektörel eleme yapılabilir (sadece aynı bankaları karşılaştır vb.)
            # Ancak basitlik adına tüm çapraz kombinasyonlara (n*(n-1)/2) bakıyoruz.
            for i in range(n_symbols):
                for j in range(i + 1, n_symbols):
                    S1 = df_prices[symbols[i]]
                    S2 = df_prices[symbols[j]]

                    # Engle-Granger Eşbütünleşme Testi
                    # score, p-value, ...
                    score, p_value, _ = coint(S1, S2)

                    # P-değeri 0.05'ten küçükse (Yani iki hisse arasındaki fark %95 olasılıkla durağansa)
                    if p_value < 0.05:
                        pairs.append((symbols[i], symbols[j], p_value))

            # En güçlü (P-value en düşük) eşbütünleşmeye sahip çiftleri listeye ekle
            pairs.sort(key=lambda x: x[2])
            self.cointegrated_pairs = pairs

            logger.info(f"Tarama tamamlandı. Bulunan eşbütünleşik çift sayısı: {len(pairs)}")
            for p in pairs[:5]: # Sadece en iyi 5'ini bas
                 logger.debug(f"Çift: {p[0]} - {p[1]} | P-Value: {p[2]:.4f}")

            return pairs

        except Exception as e:
            logger.error(f"Eşbütünleşme taramasında hata: {e}")
            return []

    """
    [QUANT MİMARI NOTU - KORELASYON VS. EŞBÜTÜNLEŞME (COINTEGRATION)]
    Amatör yatırımcılar Korelasyon ile Eşbütünleşmeyi (Cointegration) sürekli
    birbirine karıştırır. İki sarhoş düşünün: Biri diğerinin 100 metre önünden
    yürüyor (Korelasyon), ama aralarındaki mesafe hiç kapanmıyor. Veya iki köpek
    sahibi düşünün: Köpekler rastgele koşturuyor (Random Walk), ama sahiplerine
    tasmayla bağlılar. Ne kadar uzaklaşırlarsa uzaklaşsınlar, tasmadan ötürü
    eninde sonunda birbirlerine (ve sahiplerine) doğru geri çekilecekler. (Eşbütünleşme)

    Eşbütünleşme, rastgele yürüyüş gösteren iki fiyat serisinin (Örn: AKBNK ve GARAN)
    doğrusal kombinasyonunun durağan (Stationary) bir zaman serisi yarattığı durumdur.
    İki bankanın fiyat makası (Spread) ne kadar açılırsa açılsın, istatistiksel
    olarak ortalamaya dönecektir (Mean Reverting). Pairs Trading'in sırrı buradadır;
    Piyasalar çökse bile bu spread eninde sonunda kapanır. Siz piyasa yönünü
    değil, bu makasın kapanmasını oynarsınız.
    (BİST'te açığa satış yoksa, "Göreceli Ucuz" olanı Al-Tut yaparsınız).
    """
