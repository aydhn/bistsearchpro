import yfinance as yf
import numpy as np
import logging

logger = logging.getLogger(__name__)

class MacroFilter:
    """
    Borsa İstanbul'u dış şoklardan koruyacak makro risk şalteri.
    USDTRY=X oynaklığı (volatility) ve korelasyonunu takip eder.
    JP Morgan risk kurallarına göre anomali tespiti yapar.
    """

    @staticmethod
    def get_macro_risk_flag(symbol_df, symbol_name):
        """
        USDTRY=X verisini çeker, son 30 günlük oynaklığı ve Pearson korelasyonunu hesaplar.
        Eğer döviz kuru oynaklığı son 1 yılın 95. yüzdelik dilimini aşarsa macro_risk_flag = True döner.
        """
        macro_risk_flag = False
        try:
            # 1. USDTRY=X Verisi Çekme
            usd_ticker = yf.Ticker("USDTRY=X")
            # En az 1 yıllık veri alalım ki 95. yüzdelik dilimi hesaplayabilelim
            usd_df = usd_ticker.history(period="1y")

            if usd_df.empty or len(usd_df) < 250:
                logger.warning("Yetersiz USDTRY=X verisi. Makro filtre atlanıyor.")
                return False

            usd_close = usd_df['Close']

            # 2. Döviz Kuru Günlük Oynaklık (Daily Volatility)
            usd_returns = usd_close.pct_change().dropna()

            # Son 30 günlük hareketli standart sapma (oynaklık)
            rolling_volatility = usd_returns.rolling(window=30).std() * np.sqrt(252) # Yıllıklandırılmış
            rolling_volatility = rolling_volatility.dropna()

            if rolling_volatility.empty:
                return False

            # Mevcut oynaklık
            current_volatility = rolling_volatility.iloc[-1]

            # Tarihsel 95. yüzdelik dilim
            volatility_95th_percentile = np.percentile(rolling_volatility, 95)

            # 3. Anomali Tespiti (Veto Şartı)
            if current_volatility > volatility_95th_percentile:
                macro_risk_flag = True
                logger.critical(f"MAKRO RİSK UYARISI: USDTRY oynaklığı ({current_volatility:.4f}) son 1 yılın 95. yüzdelik dilimini ({volatility_95th_percentile:.4f}) aştı. Tüm yeni pozisyonlar VETO edildi.")

            # 4. Hisse ile Korelasyon (İsteğe bağlı analiz için, şu an sadece flag kullanıyoruz)
            # İki seriyi tarihe göre hizalama
            common_idx = symbol_df.index.intersection(usd_df.index)
            if len(common_idx) > 30:
                sym_returns = symbol_df.loc[common_idx, 'close'].pct_change().dropna()
                usd_returns_common = usd_close.loc[common_idx].pct_change().dropna()

                # Pearson Korelasyonu
                correlation = sym_returns.corr(usd_returns_common)
                logger.info(f"{symbol_name} ile USDTRY korelasyonu (30g): {correlation:.2f}")

            return macro_risk_flag

        except Exception as e:
            logger.error(f"MacroFilter hesaplama hatası: {e}")
            # Hata durumunda sistemi durdurmamak için False dön (Risk iştahına göre True da yapılabilir)
            return False
