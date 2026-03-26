import logging
import yfinance as yf
import numpy as np

logger = logging.getLogger(__name__)

class MacroDataEngine:
    """
    Gelişmiş Öznitelik Mühendisliği (Advanced Feature Engineering)
    Web scraping (HTML kazıma) gibi kırılgan yöntemleri REDDEDEN sistemin,
    saf matematiksel ve küresel makro verilerle beslenmesini sağlayan modül.
    """
    def __init__(self):
        # Yfinance sembolleri
        self.usdtry_symbol = "TRY=X"
        self.vix_symbol = "^VIX"
        self.gold_symbol = "GC=F"

    def fetch_macro_features(self):
        """
        Dolar/TL kuru (USDTRY), CBOE Volatilite Endeksi (VIX) ve Altın
        gibi küresel makro verilerin günlük değişim (Return) oranlarını çeker.
        Bu veriler ML modeline yeni birer "Feature" olarak eklenecektir.
        """
        features = {
            "usdtry_change": 0.0,
            "vix_change": 0.0,
            "gold_change": 0.0
        }
        try:
            # Batch download for efficiency
            data = yf.download(f"{self.usdtry_symbol} {self.vix_symbol} {self.gold_symbol}", period="2d", interval="1d", progress=False)

            if not data.empty and 'Close' in data.columns:
                closes = data['Close']

                # Calculate daily return percentage
                if len(closes) >= 2:
                    returns = closes.pct_change().iloc[-1] * 100.0

                    features["usdtry_change"] = returns.get(self.usdtry_symbol, 0.0)
                    features["vix_change"] = returns.get(self.vix_symbol, 0.0)
                    features["gold_change"] = returns.get(self.gold_symbol, 0.0)

            logger.info(f"Makro veriler çekildi: VIX={features['vix_change']:.2f}%, USDTRY={features['usdtry_change']:.2f}%")
            return features

        except Exception as e:
            logger.error(f"Makro veri çekiminde hata (Scraping değil, yfinance kullanıldı): {e}")
            # Zarif Hizmet Kaybı: Çökme, 0.0 olarak devam et
            return features

    @staticmethod
    def calculate_statistical_features(df):
        """
        Gelen hisse senedi DataFrame'i üzerinde, standart indikatörlerin ötesinde
        matematiksel metrikler hesaplar.
        """
        try:
            # 1. Getiri Çarpıklığı (Return Skewness):
            # Son 20 mumluk getirilerin asimetrisi.
            # Pozitif çarpıklık: piyasa yavaş düşüp hızlı yükselir.
            # Negatif çarpıklık: piyasa yavaş yükselip aniden çöker (Asansör formasyonu).
            if 'close' in df.columns:
                returns = df['close'].pct_change()
                skewness = returns.rolling(window=20).skew()
                df['return_skewness'] = skewness

            # 2. VWAP Uzaklığı (Eğer volume varsa basit VWAP hesabı)
            if 'volume' in df.columns and 'close' in df.columns and 'high' in df.columns and 'low' in df.columns:
                # Typical Price
                tp = (df['high'] + df['low'] + df['close']) / 3
                # Cumulative Volume and Typical Price * Volume
                # For simplicity, calculating a rolling 20-period VWAP
                rolling_vol = df['volume'].rolling(window=20).sum()
                rolling_tp_vol = (tp * df['volume']).rolling(window=20).sum()

                vwap = rolling_tp_vol / rolling_vol
                df['vwap_distance_pct'] = ((df['close'] - vwap) / vwap) * 100.0

            # 3. Hurst Exponent (Basitleştirilmiş)
            # Zaman serisinin karakterini belirler: < 0.5 (Mean Reverting), 0.5 (Random Walk), > 0.5 (Trending)
            # Vektörel bir yaklaşım: Log getiri varyanslarının zamanla nasıl ölçeklendiğine bakılır.
            # Tam hesaplama yavaştır, burada ML'e yedirebileceğimiz basit bir metrik:
            # Volatility of 20-day returns vs 5-day returns
            var_20 = returns.rolling(window=20).var()
            var_5 = returns.rolling(window=5).var()

            # This is a proxy feature. True Hurst requires rescaled range analysis.
            df['hurst_proxy'] = np.log(var_20 / var_5) / np.log(20 / 5)

            # Fill NAs
            df.fillna(0, inplace=True)
            return df

        except Exception as e:
            logger.error(f"İstatistiksel özellik hesaplama hatası: {e}")
            return df

    """
    [QUANT MİMARI NOTU - MAKRO KORELASYONLAR VE MODEL SAĞLAMLIĞI (ROBUSTNESS)]
    Neden Investing veya KAP'tan HTML (Scraping) verisi kazıyarak (P/E oranları,
    kar payları vs.) modelimizi beslemiyoruz?
    Çünkü web siteleri tasarım değiştirir. HTML etiketleri bozulur. Algoritmanız,
    tam da piyasanın çöktüğü gün bir <div> etiketi değişti diye durursa
    kasanızı sıfırlarsınız. Bu bir amatörlüktür.

    Makine öğrenimi modelleri (Random Forest/XGBoost), CBOE VIX endeksinin günlük
    değişimine, Dolar/TL'nin şoklarına ve Hurst Exponent gibi saf matematiksel
    serilerin fraktal yapılarına çok daha duyarlıdır.
    Bu veriler Bloomberg API'den (veya yfinance'tan) sayısal olarak kesintisiz akar.
    Biz "Haber ne oldu?" diye sormayız. "Dolar ve Korku Endeksi zıpladığında
    bu hisse tarihsel olarak nasıl tepki vermiş?" sorusunu ML ile modele sorarız.
    """
