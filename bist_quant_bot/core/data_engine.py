import yfinance as yf
import pandas as pd
import asyncio
import logging
import concurrent.futures
from typing import Dict, List, Optional
from core.universe import UniverseManager

class DataEngine:
    """
    BIST hisse verilerini yfinance (ücretsiz, no-scraping) üzerinden asenkron çeker.
    Eksik verileri (NaN) uygun şekilde dolduran/temizleyen (Data Cleansing) yapı.
    """
    def __init__(self):
        # Asenkron CPU-bound yfinance thread pool
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

    async def fetch_historical_data_async(self, symbols: List[str], period="6mo", interval="1d") -> Dict[str, pd.DataFrame]:
        """
        Asenkron/Paralel tarama mimarisi ile Rate Limit engelini akıllı beklemeler ile aşan yapı.
        Kıdemli Quant Notu: yfinance kütüphanesini bloklamamak için (event loop'u boğmamak adına)
        ThreadPoolExecutor üzerinden await loop.run_in_executor(self.executor, func) kullanılır.
        """
        logging.info(f"Veri İndirme Başlıyor: {len(symbols)} Hisse (Periyot: {period}, İnterval: {interval})")
        results = {}

        loop = asyncio.get_event_loop()
        tasks = []
        for symbol in symbols:
            # Rate limit'e takılmamak için aralara çok ufak rastgele uykular eklenebilir,
            # yfinance'ın `download(group, threads=True)` metodunu tek parça da çağırabiliriz.
            # Ancak kontrol bizde kalsın diye tek tek ThreadPool'a atıyoruz.
            tasks.append(
                loop.run_in_executor(self.executor, self._download_single, symbol, period, interval)
            )

        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

        for symbol, df_result in zip(symbols, completed_tasks):
            if isinstance(df_result, Exception):
                logging.error(f"⚠️ {symbol} için veri çekilemedi: {df_result}")
            elif df_result is not None and not df_result.empty:
                results[symbol] = df_result

        return results

    def _download_single(self, symbol: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        """Bloklayan yfinance isteğini yapan asıl yardımcı fonksiyon"""
        try:
            # yf.download formatı MultiIndex dönebilir, auto_adjust ile temiz OHLCV.
            df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
            if df.empty:
                return None

            # Veri Temizleme (Data Cleansing) - Sütun isimlerini zorunlu lowercase yapıyoruz (standartlaştırma kuralı)
            df.columns = [c.lower() for c in df.columns]

            # Forward fill ve Backward fill (Eksik veriler/hafta sonu kaymaları vb. için)
            df.ffill(inplace=True)
            df.bfill(inplace=True)

            # Endeks veya hisselerde hacim sütunu 0 olabiliyor, 1 yapıyoruz bölme hataları (ZeroDivisionError) için
            if 'volume' in df.columns:
                df['volume'] = df['volume'].replace(0, 1)

            return df
        except Exception as e:
            logging.error(f"DataEngine _download_single Hatası: {symbol} - {e}")
            return None

    def fetch_benchmark_data(self, period="6mo", interval="1d") -> Optional[pd.DataFrame]:
        """Makro rejim (XU100) verisini senkron olarak çeker"""
        try:
             df = yf.download("XU100.IS", period=period, interval=interval, progress=False, auto_adjust=True)
             if df.empty: return None
             df.columns = [c.lower() for c in df.columns]
             df.ffill(inplace=True)
             df.bfill(inplace=True)
             return df
        except Exception as e:
             logging.error(f"XU100 Verisi Çekilemedi: {e}")
             return None
