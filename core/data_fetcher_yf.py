import yfinance as yf
import pandas as pd
import time
import logging

logger = logging.getLogger(__name__)

class YfDataEngine:
    """
    BİST verilerini çekmek için tamamen ücretsiz ve güvenilir Yahoo Finance (yfinance) wrapper sınıfı.
    Sıfır bütçe kuralına uyar, rate limitleri yönetir ve OOP prensiplerine göre tasarlanmıştır.
    """
    def __init__(self):
        logger.info("YfDataEngine başlatıldı.")
        self.request_delay = 1.5  # IP ban yememek için her istek arası 1.5 saniye bekleme süresi.

    def fetch_ohlcv(self, symbol, interval="1h", n_bars=500):
        """
        Yahoo Finance üzerinden OHLCV verisi çeker.
        interval: yfinance formatında aralık (örn: '1h', '1d').
        symbol: yfinance formatında sembol (örn: 'THYAO.IS').
        """
        # IP ban riskine karşı rate-limit koruması
        time.sleep(self.request_delay)

        try:
            # Sembolün '.IS' eki aldığından emin ol
            if not symbol.endswith(".IS"):
                symbol = f"{symbol}.IS"

            logger.debug(f"{symbol} için {interval} periyodunda veri çekiliyor...")
            ticker = yf.Ticker(symbol)

            # Intraday (gün içi) veriler yfinance'ta en fazla son 730 gün için çekilebilir.
            period = "max"
            if interval in ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h']:
                period = "730d"

            # Vektörel çekim işlemi
            df = ticker.history(period=period, interval=interval)

            if df is None or df.empty:
                logger.warning(f"Yahoo Finance {symbol} için boş DataFrame döndürdü.")
                return pd.DataFrame()

            # İndeksleri saat dilimine (TSİ) göre standardize et
            df.index = pd.to_datetime(df.index)
            if df.index.tz is None:
                df.index = df.index.tz_localize('Europe/Istanbul')
            else:
                df.index = df.index.tz_convert('Europe/Istanbul')

            # Tüm veri kaynakları (tvdatafeed vs yfinance) arasında tutarlılık sağlamak için
            # sütun isimleri küçük harfe (lowercase) çevriliyor.
            df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            }, inplace=True)

            # Sadece ihtiyacımız olan fiyat ve hacim sütunlarını tutalım
            df = df[['open', 'high', 'low', 'close', 'volume']]

            # Na değerleri ileriye dönük doldur (forward fill - vektörel)
            df.ffill(inplace=True)

            # Sadece istenilen son N mumu döndür
            return df.tail(n_bars)

        except Exception as e:
            logger.error(f"YfDataEngine fetch_ohlcv hatası ({symbol}): {str(e)}")
            # Çökmek yerine boş DataFrame dönerek ana döngünün devam etmesini sağla
            return pd.DataFrame()
