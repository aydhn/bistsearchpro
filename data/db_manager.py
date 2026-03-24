import sqlite3
import pandas as pd
from config.settings import config
import logging
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.db_path = config.DB_PATH
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """
        Creates necessary tables and composite indexes.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # OHLCV table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv (
                    symbol TEXT,
                    timeframe TEXT,
                    datetime TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    PRIMARY KEY (symbol, timeframe, datetime)
                )
            """)

            # Fundamentals table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fundamentals (
                    symbol TEXT PRIMARY KEY,
                    pe_ratio REAL,
                    pb_ratio REAL,
                    market_cap REAL,
                    last_updated TEXT
                )
            """)

            # Paper wallet / State
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_wallet (
                    id INTEGER PRIMARY KEY,
                    balance REAL,
                    last_updated TEXT
                )
            """)

            # Open positions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS open_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    direction TEXT,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    lot_size INTEGER,
                    entry_time TEXT
                )
            """)

            conn.commit()
            logger.info("Database initialized successfully.")

    def save_bars(self, symbol, timeframe, df):
        """
        UPSERTs OHLCV dataframe into SQLite using a highly optimized vectorized approach.
        """
        if df is None or df.empty:
            return

        # Pre-calculate column indices to avoid repeated string lookups or dictionary creation in the loop.
        # This approach is significantly faster and more robust than itertuples(name='Pandas')
        # especially when column names are not valid Python identifiers.
        cols = [c.lower() for c in df.columns]

        try:
            idx_open = cols.index('open') + 1 # +1 because Index is at pos 0 in itertuples(name=None)
            idx_high = cols.index('high') + 1
            idx_low = cols.index('low') + 1
            idx_close = cols.index('close') + 1
            idx_volume = cols.index('volume') + 1
        except ValueError as e:
            logger.error(f"Required OHLCV column missing: {e}")
            return

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Use a generator expression with itertuples(name=None) for maximum performance (returns plain tuples)
            # This avoids the overhead of namedtuple creation and attribute/key lookups.
            records = (
                (
                    symbol,
                    timeframe,
                    str(row[0]), # Index
                    row[idx_open],
                    row[idx_high],
                    row[idx_low],
                    row[idx_close],
                    row[idx_volume]
                )
                for row in df.itertuples(index=True, name=None)
            )

            cursor.executemany("""
                INSERT OR REPLACE INTO ohlcv
                (symbol, timeframe, datetime, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, records)

            conn.commit()
            logger.debug(f"Saved {len(df)} bars for {symbol} ({timeframe}) to SQLite.")

    def load_bars(self, symbol, timeframe, limit=1000):
        """
        Loads optimized DataFrame from SQLite.
        """
        with self.get_connection() as conn:
            query = f"""
                SELECT datetime, open, high, low, close, volume
                FROM ohlcv
                WHERE symbol = ? AND timeframe = ?
                ORDER BY datetime DESC
                LIMIT ?
            """

            df = pd.read_sql_query(query, conn, params=(symbol, timeframe, limit))

            if df.empty:
                return df

            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            df.sort_index(ascending=True, inplace=True) # Return oldest first

            return df
