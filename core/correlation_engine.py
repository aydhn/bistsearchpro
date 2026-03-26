import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class CorrelationEngine:
    """
    Dinamik Korelasyon Matrisi.
    Sistemin tek bir sektöre veya birbiriyle yüksek korelasyonlu hisselere tüm kasayı
    bağlamasını engellemek için, aktif havuzdaki hisselerin son 30 günlük kapanış
    fiyatlarından bir Pearson Korelasyon Matrisi hesaplar.
    """
    def __init__(self, data_fetcher):
        self.fetcher = data_fetcher
        self.correlation_dict = {}

    def calculate_correlation_matrix(self, symbol_list: list):
        """
        Verilen sembol listesi için (Örn: Active Universe) korelasyonları hesaplar.
        """
        logger.info("Korelasyon matrisi hesaplanıyor...")
        if not symbol_list:
             logger.warning("Korelasyon hesaplanacak sembol listesi boş.")
             return {}

        price_data = {}
        for sym in symbol_list:
             try:
                 # Fetch last 30 daily close prices
                 # To be efficient, this could pull from local SQLite cache in a real scenario
                 df = self.fetcher.fetch_ohlcv(sym, interval="1d", n_bars=30)
                 if not df.empty:
                      price_data[sym] = df['close']
             except Exception as e:
                 logger.error(f"Korelasyon için veri çekilemedi ({sym}): {e}")

        if not price_data:
             return {}

        try:
             # Fiyatları birleştirip pct_change alarak getiri korelasyonu (daha sağlıklıdır)
             # Veya direkt fiyat korelasyonu (Pearson). Biz getiriler üzerinden bakacağız.
             df_prices = pd.DataFrame(price_data)
             df_returns = df_prices.pct_change().dropna()

             corr_matrix = df_returns.corr(method='pearson')

             # Sözlük yapısına çevir: {'THYAO.IS': ['PGSUS.IS', 'TAVHL.IS'], ...}
             corr_dict = {}
             for col in corr_matrix.columns:
                  # Kendisi hariç, %80'in (+0.80) üzerinde pozitif korelasyona sahip olanlar
                  highly_correlated = corr_matrix.index[(corr_matrix[col] > 0.80) & (corr_matrix.index != col)].tolist()
                  corr_dict[col] = highly_correlated

             self.correlation_dict = corr_dict
             logger.info("Korelasyon matrisi başarıyla oluşturuldu ve güncellendi.")
             return corr_dict

        except Exception as e:
             logger.error(f"Korelasyon matrisi oluşturulurken hata: {e}")
             return {}

    def get_highly_correlated_symbols(self, symbol: str) -> list:
        """
        Belirtilen sembolle %80'in üzerinde korelasyona sahip diğer hisseleri döndürür.
        """
        return self.correlation_dict.get(symbol, [])

    """
    [QUANT MİMARI NOTU - KORELASYON VE MODERN PORTFÖY TEORİSİ]
    Markowitz'in Modern Portföy Teorisi'ne göre, portföye yeni bir varlık eklerken
    sadece beklenen getirisine bakılmaz, diğer varlıklarla olan KORELASYONUNA bakılır.

    Eğer aynı anda THYAO ve PGSUS için AL sinyali alıyorsak ve korelasyonları 0.90 ise,
    aslında iki farklı risk almıyoruz, tek bir "Havacılık Sektörü" riski alıyoruz ve
    sermaye maruziyetimizi (Exposure) ikiye katlıyoruz demektir. Havacılığı etkileyecek
    kötü bir haberde, her iki pozisyon da aynı anda stop olur ve portföyün maksimum
    düşüşünü (Max Drawdown) geometrik olarak artırır.

    Bu modül, yüksek korelasyonlu varlıklara mükerrer girişleri engelleyerek
    yatırımcının psikolojik sermayesini korur.
    """
