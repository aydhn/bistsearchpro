import logging
from datetime import datetime
from data.db_manager import DatabaseManager
from telegram_bot.notifier import TelegramNotifier
from core.risk_manager import RiskManager
import json

logger = logging.getLogger(__name__)

class PaperTrader:
    """
    Sanal bakiye ile açık pozisyonları takip eden, SL/TP seviyelerine
    değip değmediğini kontrol eden modül.
    """
    def __init__(self, db_manager: DatabaseManager, notifier: TelegramNotifier, risk_manager: RiskManager = None):
        self.db = db_manager
        self.notifier = notifier
        self.rm = risk_manager or RiskManager()
        self._initialize_wallet()

    def _initialize_wallet(self):
        """
        Sanal cüzdan yoksa varsayılan bir bakiye (örn. 100.000 TL) ile başlatır.
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS paper_wallet (
                        id INTEGER PRIMARY KEY,
                        balance REAL,
                        last_updated TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS open_positions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT,
                        direction TEXT,
                        entry_price REAL,
                        stop_loss REAL,
                        take_profit REAL,
                        lot_size REAL,
                        entry_time TEXT
                    )
                """)

                cursor.execute("SELECT balance FROM paper_wallet WHERE id = 1")
                row = cursor.fetchone()
                if not row:
                    cursor.execute(
                        "INSERT INTO paper_wallet (id, balance, last_updated) VALUES (1, ?, ?)",
                        (100000.0, datetime.now().isoformat())
                    )
                    conn.commit()
                    logger.info("Sanal cüzdan 100.000 TL ile başlatıldı.")
        except Exception as e:
            logger.error(f"Sanal cüzdan başlatılırken hata: {e}")

    def get_balance(self):
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT balance FROM paper_wallet WHERE id = 1")
                row = cursor.fetchone()
                return row[0] if row else 0.0
        except Exception as e:
            logger.error(f"Bakiye okuma hatası: {e}")
            return 0.0

    def update_balance(self, amount, add=True):
        current = self.get_balance()
        new_balance = current + amount if add else current - amount
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE paper_wallet SET balance = ?, last_updated = ? WHERE id = 1",
                    (new_balance, datetime.now().isoformat())
                )
                conn.commit()
            logger.info(f"Sanal cüzdan güncellendi. Yeni bakiye: {new_balance:.2f} TL")
            return new_balance
        except Exception as e:
            logger.error(f"Bakiye güncelleme hatası: {e}")
            return current

    def open_position(self, symbol, direction, entry_price, stop_loss, take_profit, lot_size):
        """
        Orchestrator'dan veya position_sizer'dan gelen bilgileri açık pozisyon olarak kaydeder.
        """
        cost = entry_price * lot_size
        current_balance = self.get_balance()

        if cost > current_balance:
            logger.warning(f"Bakiye yetersiz! {symbol} için {cost:.2f} TL gerekiyor, bakiye: {current_balance:.2f} TL")
            return False

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO open_positions
                    (symbol, direction, entry_price, stop_loss, take_profit, lot_size, entry_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, direction, entry_price,
                    stop_loss, take_profit, lot_size,
                    datetime.now().isoformat()
                ))
                conn.commit()

            # Sanal bakiyeden düş
            self.update_balance(cost, add=False)

            logger.info(f"Paper Trade Açıldı: {symbol} {direction} @ {entry_price:.2f} (Lot: {lot_size:.2f})")
            return True
        except Exception as e:
            logger.error(f"Pozisyon açma hatası: {e}")
            return False

    async def check_open_positions(self, current_data: dict):
        """
        current_data: {'THYAO.IS': {'close': 250.5, 'atr': 2.5}, ...} formatında güncel fiyat/atr sözlüğü.
        Saat başı veya belirli periyotlarda çağrılarak SL/TP ve Trailing Stop kontrolü yapar.
        Faz 14 (Dinamik Yönetim) gereğince güncellenmiştir.
        """
        closed_trades = []
        ids_to_delete = []
        total_revenue = 0.0

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM open_positions")
                positions = cursor.fetchall()

                for pos in positions:
                    pos_id, symbol, direction, entry_price, sl, tp, lot_size, entry_time = pos

                    symbol_data = current_data.get(symbol)
                    if not symbol_data:
                        continue

                    current_price = symbol_data.get('close')
                    current_atr = symbol_data.get('atr', 0.0) # ATR bilgisi yoksa 0

                    if current_price is None:
                        continue

                    # Dinamik Çıkış Kontrolü (Phase 14)
                    res = self.rm.evaluate_dynamic_exit(
                        symbol, current_price, entry_price, sl, tp, entry_time, current_atr, lot_size, direction
                    )

                    action = res.get('action')
                    message = res.get('message', '')
                    new_sl = res.get('new_sl', sl)
                    close_ratio = res.get('close_ratio', 0.0)

                    # 1. Stop Güncelleme (Trailing veya Breakeven)
                    if action == 'UPDATE_SL' and new_sl != sl:
                        cursor.execute("UPDATE open_positions SET stop_loss = ? WHERE id = ?", (new_sl, pos_id))
                        conn.commit()
                        if message:
                            await self.notifier.send_system_alert(message, level="INFO")

                    # 2. Geleneksel SL/TP Kesişimleri
                    close_price = None
                    reason = ""

                    if direction.upper() == "BUY":
                        if current_price <= new_sl:
                            close_price = current_price
                            reason = "STOP LOSS / TRAILING STOP"
                            close_ratio = 1.0
                        elif current_price >= tp:
                            close_price = current_price
                            reason = "TAKE PROFIT"
                            close_ratio = 1.0
                    else: # SELL
                        if current_price >= new_sl:
                            close_price = current_price
                            reason = "STOP LOSS / TRAILING STOP"
                            close_ratio = 1.0
                        elif current_price <= tp:
                            close_price = current_price
                            reason = "TAKE PROFIT"
                            close_ratio = 1.0

                    # 3. Dinamik Çıkış Aksiyonları (Zaman Aşımı / Kısmi Kapanış)
                    if close_price is None and action in ['PARTIAL_CLOSE', 'FULL_CLOSE_TIMEOUT']:
                        close_price = current_price
                        reason = action
                        if message:
                             await self.notifier.send_system_alert(message, level="INFO")

                    if close_price is not None and close_ratio > 0.0:
                        # Kapanacak lot miktarı
                        closed_lot = lot_size * close_ratio

                        # PnL Hesaplama
                        if direction.upper() == "BUY":
                            pnl = (close_price - entry_price) * closed_lot
                            revenue = (close_price * closed_lot)
                        else:
                            pnl = (entry_price - close_price) * closed_lot
                            revenue = ((entry_price * 2 - close_price) * closed_lot)

                        total_revenue += revenue

                        if close_ratio >= 1.0:
                            ids_to_delete.append((pos_id,))
                        else:
                            # Kısmi Kapanış: Kalan lotu DB'de güncelle
                            new_lot = lot_size - closed_lot
                            cursor.execute("UPDATE open_positions SET lot_size = ?, stop_loss = ? WHERE id = ?", (new_lot, new_sl, pos_id))
                            conn.commit()

                        msg = f"📉 *POZİSYON KAPANDI (PAPER TRADE)* 📈\n\n" \
                              f"Sembol: {symbol}\n" \
                              f"Sebep: {reason}\n" \
                              f"Giriş: {entry_price:.2f}\n" \
                              f"Çıkış: {close_price:.2f}\n" \
                              f"Kâr/Zarar: {pnl:.2f} TL\n" \
                              f"Lot: {closed_lot:.2f}"

                        closed_trades.append(msg)

                if ids_to_delete:
                    cursor.executemany("DELETE FROM open_positions WHERE id = ?", ids_to_delete)
                    conn.commit()

            if total_revenue > 0:
                new_bal = self.update_balance(total_revenue, add=True)
                closed_trades = [msg + f"\nYeni Bakiye: {new_bal:.2f} TL" for msg in closed_trades]

            # Telegram bildirimleri
            for msg in closed_trades:
                await self.notifier.send_system_alert(msg, level="INFO")

            return len(closed_trades)

        except Exception as e:
            logger.error(f"Açık pozisyon kontrolünde hata: {e}")
            return 0
