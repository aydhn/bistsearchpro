import logging
from core.data_fetcher_tv import TvDataEngine
from core.data_fetcher_yf import YfDataEngine
from core.universe import SymbolUniverse

logger = logging.getLogger(__name__)

class DataRouter:
    def __init__(self):
        self.tv_engine = TvDataEngine()
        self.yf_engine = YfDataEngine()
        self.universe = SymbolUniverse()
        logger.info("DataRouter initialized.")

    def get_data(self, symbol, interval, n_bars=1000):
        """
        Orchestrates fetching data from primary (tvdatafeed) and fallback (yfinance).
        interval_type handles the translation between library intervals.
        """

        # Translate interval for tvdatafeed (e.g. '1H' -> Interval.in_1_hour)
        tv_interval = interval # Assume mapping is done externally or here
        tv_symbol = self.universe.map_symbol(symbol, source="tv")

        try:
            logger.debug(f"Attempting fetch from TvDataEngine for {symbol}")
            return self.tv_engine.fetch_ohlcv(tv_symbol, tv_interval, n_bars)

        except Exception as e:
            logger.warning(f"Birincil veri kaynağı çöktü ({symbol}), Fallback aktif: {e}")

            yf_interval = "1h" # Map appropriately based on input
            if interval == "1D": yf_interval = "1d"

            yf_symbol = self.universe.map_symbol(symbol, source="yf")
            try:
                logger.debug(f"Attempting fallback fetch from YfDataEngine for {symbol}")
                return self.yf_engine.fetch_ohlcv(yf_symbol, yf_interval, n_bars)
            except Exception as e:
                logger.error(f"Fallback data fetch also failed for {symbol}: {e}")
                raise
