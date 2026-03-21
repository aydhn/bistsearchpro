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
        UPSERTs OHLCV dataframe into SQLite.
        """
        if df.empty:
            return

        with self.get_connection() as conn:
            cursor = conn.cursor()

            records = []
            for index, row in df.iterrows():
                # Extract index as string properly handling timezone
                dt_str = str(index)

                # Fetch typical columns. Depending on TV/YF, columns might be lowercase or capitalized.
                # Assuming data_fetcher standardize to lower/upper. Let's use get to be safe.
                o = row.get('open', row.get('Open'))
                h = row.get('high', row.get('High'))
                l = row.get('low', row.get('Low'))
                c = row.get('close', row.get('Close'))
                v = row.get('volume', row.get('Volume'))

                records.append((symbol, timeframe, dt_str, o, h, l, c, v))

            cursor.executemany("""
                INSERT OR REPLACE INTO ohlcv
                (symbol, timeframe, datetime, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, records)

            conn.commit()
            logger.debug(f"Saved {len(records)} bars for {symbol} ({timeframe}) to SQLite.")

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
