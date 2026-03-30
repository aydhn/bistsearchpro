import yfinance as yf
import pandas as pd
import logging

class MarketFilter:
    """
    Piyasanın geneline (XU100) bakarak Risk-On / Risk-Off şalterini indiren/kaldıran makro risk yöneticisi.
    BIST100 endeksi %-4.8 altındaysa (Devre Kesici), tüm taramaları askıya alır.
    """
    def __init__(self, config):
        self.ema_long = config['strategy_settings']['EMA_LONG']

    def is_risk_on(self, benchmark_df: pd.DataFrame) -> bool:
        """
        XU100 güncel DataFrame'i alarak makro sağlığı test eder.
        Dönüş: True (Tarama Serbest), False (Tarama Yasak, Sadece Eldekileri Yönet)
        """
        if benchmark_df is None or benchmark_df.empty:
            logging.warning("Benchmark (XU100) verisi okunamadı. Güvenlik gereği RISK-OFF moduna geçiliyor.")
            return False

        try:
            # Vektörel trend
            benchmark_df[f'ema_{self.ema_long}'] = benchmark_df['close'].ewm(span=self.ema_long, adjust=False).mean()
            benchmark_df['pct_change'] = benchmark_df['close'].pct_change() * 100

            last_row = benchmark_df.iloc[-1]
            last_close = last_row['close']
            last_ema = last_row[f'ema_{self.ema_long}']
            last_pct = last_row['pct_change']

            # Kural 1: Fiyat, uzun vadeli hareketli ortalamanın altında (Piyasa Ayı'da)
            if last_close < last_ema:
                logging.info(f"MAKRO RİSK UYARISI: XU100 ({last_close:.2f}) EMA{self.ema_long} ({last_ema:.2f}) altında. Risk-Off.")
                return False

            # Kural 2: Flash Crash / Devre Kesici Radarı (% -4.8 ve altı)
            if last_pct <= -4.8:
                logging.warning(f"ACİL DURUM PROTOKOLÜ: XU100 Devre Kesici sınırında! (Değişim: %{last_pct:.2f}). Tüm yeni alımlar DURDURULDU.")
                return False

            logging.info("XU100 Sağlıklı. Risk-On (Savaş Modu).")
            return True

        except Exception as e:
            logging.error(f"MarketFilter hatası: {e}. Failsafe gereği RISK-OFF.")
            return False
