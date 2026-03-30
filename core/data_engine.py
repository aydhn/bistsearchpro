import yfinance as yf
import pandas as pd
import asyncio
from concurrent.futures import ThreadPoolExecutor
from core.logger_engine import LoggerEngine

logger = LoggerEngine.get_system_logger()

# Veri çekme çözümümüz "yfinance" kütüphanesidir. Ücretsizdir ve yapılandırılmış
# DataFrame döndürür. Scraping (Kazıma) YAPILMAYACAKTIR.
# Asenkron (concurrent) yapı "Rate Limit" (İstek Sınırı) engeline takılmamak için
# "Batch" (Grup) çekim mantığıyla ThreadPoolExecutor kullanır.

class DataEngine:
    def __init__(self):
        # Ayrı bir Executor havuzu, ana thread'i (Event Loop) bloklamaz.
        self.executor = ThreadPoolExecutor(max_workers=5)

    async def fetch_history_async(self, symbols, period="1mo", interval="1d"):
        """Çoklu hisse verisini eşzamanlı çeker. Hata olan hisseler elenir."""
        tasks = []
        loop = asyncio.get_running_loop()

        for sym in symbols:
            tasks.append(loop.run_in_executor(self.executor, self._download_single, sym, period, interval))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_data = {}
        for sym, res in zip(symbols, results):
            if isinstance(res, Exception):
                logger.error(f"Veri çekme hatası (Timeout/ConnectionError): {sym} -> {res}")
            elif res is not None and not res.empty:
                valid_data[sym] = res
        return valid_data

    def _download_single(self, symbol, period, interval):
        # Yfinance indirme ve temizleme (Data Cleansing).
        try:
            df = yf.download(symbol, period=period, interval=interval, progress=False, show_errors=False)
            if df.empty:
                return None

            # MultiIndex sorunlarını önleme ve isimlendirme standardizasyonu (Case-insensitive pipeline kuralı)
            df.columns = df.columns.droplevel(1) if isinstance(df.columns, pd.MultiIndex) else df.columns
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })

            # Eksik verileri (NaN) uygun şekilde dolduran Quant Developer dokunuşu
            df.ffill(inplace=True)
            df.bfill(inplace=True)
            return df
        except Exception as e:
            raise RuntimeError(f"API Yanıt vermedi: {e}")
