from tvdatafeed import TvDatafeed
import logging
import time
import pandas as pd

logger = logging.getLogger(__name__)

class TvDataEngine:
    def __init__(self):
        try:
            self.tv = TvDatafeed(auto_login=False)
            logger.info("TvDatafeed initialized anonymously.")
        except Exception as e:
             logger.error(f"TvDatafeed initialization failed: {e}")
             self.tv = None

    def fetch_ohlcv(self, symbol, interval, n_bars):
        """
        Fetches OHLCV data from TradingView.
        interval expects tvdatafeed.Interval enum (e.g. Interval.in_1_hour)
        """
        if not self.tv:
             raise Exception("TvDatafeed is not initialized.")

        max_retries = 3
        delays = [2, 4, 8]

        for i in range(max_retries):
            try:
                df = self.tv.get_hist(symbol=symbol, exchange='BIST', interval=interval, n_bars=n_bars)

                if df is None or df.empty:
                    raise Exception(f"Empty DataFrame returned for {symbol}")

                df.index = pd.to_datetime(df.index)
                if df.index.tz is None:
                    df.index = df.index.tz_localize('Europe/Istanbul')
                else:
                    df.index = df.index.tz_convert('Europe/Istanbul')

                df.ffill(inplace=True)
                return df

            except Exception as e:
                logger.warning(f"TvDataEngine fetch failed for {symbol}: {e}. Retrying in {delays[i] if i < len(delays) else delays[-1]}s...")
                time.sleep(delays[i] if i < len(delays) else delays[-1])

        logger.error(f"TvDataEngine fetch completely failed for {symbol} after {max_retries} retries.")
        raise Exception(f"TvDataEngine fetch completely failed for {symbol}")
