import logging
from datetime import datetime
from data.db_manager import DatabaseManager
from telegram.notifier import TelegramNotifier
import asyncio

logger = logging.getLogger(__name__)

class PaperTrader:
    """
    Sanal bakiye ile açık pozisyonları takip eden, SL/TP seviyelerine
    değip değmediğini kontrol eden modül.
    """
    def __init__(self, db_manager: DatabaseManager, notifier: TelegramNotifier):
        self.db = db_manager
        self.notifier = notifier
        self._initialize_wallet()

    def _initialize_wallet(self):
        """
        Sanal cüzdan yoksa varsayılan bir bakiye (örn. 100.000 TL) ile başlatır.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM paper_wallet WHERE id = 1")
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    "INSERT INTO paper_wallet (id, balance, last_updated) VALUES (1, ?, ?)",
                    (100000.0, datetime.now().isoformat())
                )
                conn.commit()
                logger.info("Sanal cüzdan 100.000 TL ile başlatıldı.")

    def get_balance(self):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM paper_wallet WHERE id = 1")
            row = cursor.fetchone()
            return row[0] if row else 0.0

    def update_balance(self, amount, add=True):
        current = self.get_balance()
        new_balance = current + amount if add else current - amount
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE paper_wallet SET balance = ?, last_updated = ? WHERE id = 1",
                (new_balance, datetime.now().isoformat())
            )
            conn.commit()
        logger.info(f"Sanal cüzdan güncellendi. Yeni bakiye: {new_balance:.2f} TL")
        return new_balance

    def open_position(self, signal):
        """
        Orchestrator'dan gelen SignalResponse nesnesini açık pozisyon olarak kaydeder.
        Bunu yapabilmek için RiskManager'dan alınan lot bilgisine de ihtiyaç var.
        Bu versiyonda basitçe lot_size = 1 varsayıyoruz (RiskManager çağrıldığında o verecektir).
        """
        # RiskManager entegrasyonu (Basit Lot Hesaplama)
        # Gerçek kodda lot, signal veya RiskManager üzerinden gelmeli.
        # Varsayılan lot 1
        lot_size = 1

        cost = signal.entry_price * lot_size
        current_balance = self.get_balance()

        if cost > current_balance:
            logger.warning(f"Bakiye yetersiz! {signal.symbol} için {cost:.2f} TL gerekiyor, bakiye: {current_balance:.2f} TL")
            return False

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO open_positions
                (symbol, direction, entry_price, stop_loss, take_profit, lot_size, entry_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.symbol, signal.direction, signal.entry_price,
                signal.stop_loss, signal.take_profit, lot_size,
                datetime.now().isoformat()
            ))
            conn.commit()

        # Sanal bakiyeden düş (Opsiyonel: Marjin blokajı gibi düşünülebilir, PnL kapandığında geri yansır)
        self.update_balance(cost, add=False)

        logger.info(f"Paper Trade Açıldı: {signal.symbol} {signal.direction} @ {signal.entry_price:.2f}")
        return True

    async def check_open_positions(self, current_prices: dict):
        """
        current_prices: {'THYAO': 250.5, 'AKBNK': 45.2, ...} formatında güncel fiyat sözlüğü.
        Saat başı veya belirli periyotlarda çağrılarak SL/TP kontrolü yapar.
        """
        closed_trades = []
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM open_positions")
            positions = cursor.fetchall()

            for pos in positions:
                # Kolon sıralaması: id(0), symbol(1), direction(2), entry_price(3), stop_loss(4), take_profit(5), lot(6), time(7)
                pos_id, symbol, direction, entry_price, sl, tp, lot_size, _ = pos

                current_price = current_prices.get(symbol)
                if not current_price:
                    continue

                close_price = None
                reason = ""

                if direction.upper() == "BUY":
                    if current_price <= sl:
                        close_price = current_price
                        reason = "STOP LOSS"
                    elif current_price >= tp:
                        close_price = current_price
                        reason = "TAKE PROFIT"
                elif direction.upper() == "SELL":
                    if current_price >= sl:
                        close_price = current_price
                        reason = "STOP LOSS"
                    elif current_price <= tp:
                        close_price = current_price
                        reason = "TAKE PROFIT"

                if close_price is not None:
                    # Pozisyonu kapat
                    cursor.execute("DELETE FROM open_positions WHERE id = ?", (pos_id,))

                    # PnL Hesaplama (Çift Yönlü düşünülmüş)
                    if direction.upper() == "BUY":
                        pnl = (close_price - entry_price) * lot_size
                    else:
                        pnl = (entry_price - close_price) * lot_size

                    # Ana parayı ve karı/zararı cüzdana geri ekle
                    revenue = (entry_price * lot_size) + pnl
                    new_bal = self.update_balance(revenue, add=True)

                    msg = f"📉 *POZİSYON KAPANDI* 📈\n\n" \
                          f"Sembol: {symbol}\n" \
                          f"Sebep: {reason}\n" \
                          f"Giriş: {entry_price:.2f}\n" \
                          f"Çıkış: {close_price:.2f}\n" \
                          f"Kâr/Zarar: {pnl:.2f} TL\n" \
                          f"Yeni Bakiye: {new_bal:.2f} TL"

                    closed_trades.append(msg)

            conn.commit()

        # Telegram bildirimleri
        for msg in closed_trades:
            # Kaçış karakterlerini varsayılan markdown'a göre ayarlıyoruz
            # Notifier kendi içinde escape edecektir veya biz basit metin atarız
            await self.notifier.send_system_alert(msg, level="INFO")

        return len(closed_trades)
