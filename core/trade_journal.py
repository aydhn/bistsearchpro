import logging
from datetime import datetime
import pandas as pd
from data.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class TradeJournal:
    """
    Sistemin o anki "karar alma mekanizmasını" şeffafça belgeleyen loglama sınıfı.
    Geriye dönük incelenebilir (audit trail) bir yapı sağlar.
    Faz 17 ile uyumlu olarak SQLite veritabanına doğrudan kayıt yapar.
    """
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._initialize_table()

    def _initialize_table(self):
        """
        trade_journal tablosunu oluşturur (henüz yoksa).
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trade_journal (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        symbol TEXT,
                        direction TEXT,
                        entry_price REAL,
                        stop_loss REAL,
                        take_profit REAL,
                        rsi_value REAL,
                        atr_value REAL,
                        kelly_lot REAL,
                        strategy_source TEXT,
                        market_regime TEXT,
                        ml_prob REAL,
                        status TEXT,
                        exit_price REAL,
                        pnl REAL,
                        exit_reason TEXT
                    )
                """)
                conn.commit()
                logger.info("Trade Journal (trade_journal) tablosu başlatıldı.")
        except Exception as e:
            logger.error(f"Trade Journal tablo oluşturma hatası: {e}")

    def log_entry(self, symbol: str, direction: str, entry_price: float, sl: float, tp: float,
                  rsi: float, atr: float, lot: float, source: str, regime: str, prob: float):
        """
        İşleme girildiğinde kayıt atar.
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO trade_journal
                    (timestamp, symbol, direction, entry_price, stop_loss, take_profit,
                     rsi_value, atr_value, kelly_lot, strategy_source, market_regime,
                     ml_prob, status, exit_price, pnl, exit_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(), symbol, direction, entry_price, sl, tp,
                    rsi, atr, lot, source, regime, prob, "OPEN", 0.0, 0.0, ""
                ))
                conn.commit()
                logger.debug(f"Trade Journal'a ENTRY kaydı eklendi: {symbol} {direction}")
        except Exception as e:
            logger.error(f"Trade Journal entry loglama hatası: {e}")

    def log_exit(self, symbol: str, exit_price: float, pnl: float, exit_reason: str):
        """
        İşlem kapatıldığında (SL/TP) kaydı günceller.
        Birden fazla aynı sembol açık olabilir, en eskisini veya ID'ye göre olanı kapatmak idealdir.
        Burada basitlik için en son açılan açık pozisyonu bulup kapatacağız.
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                # Find the most recent OPEN trade for this symbol
                cursor.execute("""
                    SELECT id FROM trade_journal
                    WHERE symbol = ? AND status = 'OPEN'
                    ORDER BY id DESC LIMIT 1
                """, (symbol,))

                row = cursor.fetchone()
                if row:
                    trade_id = row[0]
                    cursor.execute("""
                        UPDATE trade_journal
                        SET status = 'CLOSED', exit_price = ?, pnl = ?, exit_reason = ?
                        WHERE id = ?
                    """, (exit_price, pnl, exit_reason, trade_id))
                    conn.commit()
                    logger.debug(f"Trade Journal'da EXIT kaydı güncellendi: {symbol} PnL={pnl:.2f}")
                else:
                    logger.warning(f"Trade Journal'da kapatılacak AÇIK işlem bulunamadı: {symbol}")
        except Exception as e:
            logger.error(f"Trade Journal exit loglama hatası: {e}")

    def export_to_csv(self, filename="logs/trade_journal.csv"):
        """
        Gerekirse veritabanındaki kayıtları analist incelemesi için CSV'ye döker.
        """
        try:
            with self.db.get_connection() as conn:
                query = "SELECT * FROM trade_journal"
                df = pd.read_sql_query(query, conn)
                df.to_csv(filename, index=False)
                logger.info(f"Trade Journal başarıyla {filename} dosyasına aktarıldı.")
        except Exception as e:
            logger.error(f"Trade Journal CSV dışa aktarma hatası: {e}")
