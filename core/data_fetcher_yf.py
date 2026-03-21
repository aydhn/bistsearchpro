import yfinance as yf
import pandas as pd
import time
import logging

logger = logging.getLogger(__name__)

class YfDataEngine:
    def __init__(self):
        logger.info("YfDataEngine initialized.")

    def fetch_ohlcv(self, symbol, interval, n_bars):
        """
        Fetches OHLCV data from Yahoo Finance.
        interval expects yfinance interval format (e.g., "1h", "1d")
        symbol should be in yfinance format (e.g., THYAO.IS)
        """
        # Sleep to avoid quick rate limits
        time.sleep(1)

        try:
            ticker = yf.Ticker(symbol)
            # n_bars translates roughly to a period or we fetch max and slice.
            # Using period="max" and slicing the tail is safer for generic intervals if supported.
            # For 1h, max is 730d. Let's just fetch 730d and slice.
            period = "max"
            if interval in ['1m', '2m', '5m', '15m', '30m', '90m', '1h']:
                 period = "730d" # yf limit for intraday

            df = ticker.history(period=period, interval=interval)

            if df.empty:
                raise Exception(f"Empty DataFrame from Yahoo Finance for {symbol}")

            # Standardize index
            df.index = pd.to_datetime(df.index)
            if df.index.tz is None:
                df.index = df.index.tz_localize('Europe/Istanbul')
            else:
                df.index = df.index.tz_convert('Europe/Istanbul')

            # Rename columns to match tvdatafeed format if necessary
            df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)

            df.ffill(inplace=True)
            return df.tail(n_bars)

        except Exception as e:
            logger.error(f"YfDataEngine fetch failed for {symbol}: {e}")
            raise
