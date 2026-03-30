import json
import sqlite3
import os
import shutil
import hashlib
from datetime import datetime
from config.config_manager import ConfigManager
from core.logger_engine import LoggerEngine
from collections import defaultdict

logger = LoggerEngine.get_trade_logger()

# "Araf (Pending State)" mantığı ile çalışan, fon yöneticisinin manuel onayını bekleyen
# yarı otonom (Human-in-the-Loop) bir portföy yöneticisi.
# Çıkış Motoru (Exit Engine) dinamik "Trailing Stop" mekanizması ile risk yönetimi sağlar.
# Veri bütünlüğünü sağlamak için Atomik Yazma (Atomic Write) ve yedekleme barındırır.

class PortfolioManager:
    def __init__(self, db_path="data/portfolio.db", temp_db_path="data/portfolio_temp.db"):
        self.db_path = db_path
        self.temp_db_path = temp_db_path
        self._init_db()
        self.sync_balance()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Sanal Kasa Tablosu
        cursor.execute('''CREATE TABLE IF NOT EXISTS balance (
                            id INTEGER PRIMARY KEY,
                            current_balance REAL)''')

        # Açık Pozisyonlar Tablosu (Gerçek işlem)
        cursor.execute('''CREATE TABLE IF NOT EXISTS open_positions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            symbol TEXT,
                            entry_price REAL,
                            current_sl REAL,
                            take_profit REAL,
                            lot_size INTEGER,
                            cost REAL,
                            timestamp TEXT)''')

        # İşlem Geçmişi / Kapalı Pozisyonlar Tablosu
        cursor.execute('''CREATE TABLE IF NOT EXISTS trade_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            symbol TEXT,
                            entry_price REAL,
                            exit_price REAL,
                            lot_size INTEGER,
                            pnl REAL,
                            pnl_percent REAL,
                            entry_time TEXT,
                            exit_time TEXT)''')

        # Bekleyen Sinyaller Tablosu (Human-in-the-Loop)
        cursor.execute('''CREATE TABLE IF NOT EXISTS pending_signals (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            symbol TEXT,
                            entry_price REAL,
                            stop_loss REAL,
                            take_profit REAL,
                            lot_size INTEGER,
                            cost REAL,
                            timestamp TEXT)''')

        # Başlangıç bakiyesi kontrolü
        cursor.execute("SELECT current_balance FROM balance WHERE id = 1")
        result = cursor.fetchone()
        if not result:
            initial_balance = float(ConfigManager.get("trading_parameters", "INITIAL_VIRTUAL_BALANCE") or 100000)
            cursor.execute("INSERT INTO balance (id, current_balance) VALUES (1, ?)", (initial_balance,))

        conn.commit()
        conn.close()

    def sync_balance(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT current_balance FROM balance WHERE id = 1")
        self.balance = cursor.fetchone()[0]
        conn.close()

    def get_balance(self):
        self.sync_balance()
        return self.balance

    def set_balance(self, new_balance):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE balance SET current_balance = ? WHERE id = 1", (new_balance,))
        conn.commit()
        conn.close()
        self.sync_balance()

    def get_open_positions(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM open_positions")
        columns = [col[0] for col in cursor.description]
        positions = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return positions

    def add_pending_signal(self, plan):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Daha önce bekleyen sinyal varsa güncelle, yoksa ekle.
        # (Yığılmayı önler, son güncel sinyal arafta kalır)
        cursor.execute("DELETE FROM pending_signals WHERE symbol = ?", (plan['symbol'],))

        cursor.execute('''INSERT INTO pending_signals (symbol, entry_price, stop_loss, take_profit, lot_size, cost, timestamp)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                       (plan['symbol'], plan['entry_price'], plan['stop_loss'], plan['take_profit'],
                        plan['lot_size'], plan['cost'], plan['timestamp']))
        conn.commit()
        conn.close()
        logger.info(f"Portföy Yönetimi: Sinyal arafta (bekliyor): {plan['symbol']}")

    def get_pending_signals(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pending_signals")
        columns = [col[0] for col in cursor.description]
        signals = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return signals

    def approve_signal(self, symbol, real_price, lot_size):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM pending_signals WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            logger.warning(f"Onaylanacak sinyal bulunamadı: {symbol}")
            return False, "Sinyal bulunamadı veya zaman aşımına uğradı."

        columns = [col[0] for col in cursor.description]
        signal = dict(zip(columns, row))

        # Gerçek maliyet ve Sanal Kasa Düşümü
        real_cost = real_price * lot_size
        if real_cost > self.get_balance():
            conn.close()
            return False, "Yetersiz bakiye."

        new_balance = self.get_balance() - real_cost
        self.set_balance(new_balance)

        # Açık pozisyonlara taşı (Araftan gerçeğe)
        cursor.execute('''INSERT INTO open_positions (symbol, entry_price, current_sl, take_profit, lot_size, cost, timestamp)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                       (symbol, real_price, signal['stop_loss'], signal['take_profit'], lot_size, real_cost, datetime.now().isoformat()))

        cursor.execute("DELETE FROM pending_signals WHERE symbol = ?", (symbol,))
        conn.commit()
        conn.close()

        LoggerEngine.log_audit("MANUAL_APPROVE", f"Admin onayı: {symbol} | Fiyat: {real_price} | Lot: {lot_size}")
        return True, "İşlem onaylandı, portföye eklendi."

    def reject_signal(self, symbol):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_signals WHERE symbol = ?", (symbol,))
        conn.commit()
        conn.close()
        LoggerEngine.log_audit("MANUAL_REJECT", f"Admin es geçti: {symbol}")
        return True

    def update_trailing_stop(self, symbol, current_price, current_atr):
        # Dinamik "Trailing Stop" (İzleyen Stop) mekanizması
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT entry_price, current_sl FROM open_positions WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return False

        entry_price, current_sl = row
        atr_sl_mult = float(ConfigManager.get("strategy_settings", "ATR_MULTIPLIER_SL") or 1.5)
        new_sl = current_price - (atr_sl_mult * current_atr)

        # Break Even (Başa Baş) eşiği (örn: 1.5 ATR aşıldığında SL'yi giriş fiyatına çek)
        if current_price >= entry_price + (1.5 * current_atr):
            if new_sl < entry_price:
                 new_sl = entry_price # Zarar etme riski sıfırlandı

        # Stop seviyesini SADECE yukarı taşıyabiliriz.
        if new_sl > current_sl:
            cursor.execute("UPDATE open_positions SET current_sl = ? WHERE symbol = ?", (new_sl, symbol))
            conn.commit()
            conn.close()
            logger.info(f"KORUMA GÜNCELLENDİ: {symbol} | Yeni SL: {new_sl:.2f} (Önceki: {current_sl:.2f})")
            return True, new_sl

        conn.close()
        return False, current_sl

    def close_position(self, symbol, exit_price, reason="SL/TP"):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM open_positions WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False, "Pozisyon bulunamadı."

        columns = [col[0] for col in cursor.description]
        pos = dict(zip(columns, row))

        pnl = (exit_price - pos['entry_price']) * pos['lot_size']
        pnl_percent = (exit_price - pos['entry_price']) / pos['entry_price'] * 100

        # Sanal Kasa İadesi
        new_balance = self.get_balance() + (exit_price * pos['lot_size'])
        self.set_balance(new_balance)

        # İşlem Geçmişine Kaydet
        cursor.execute('''INSERT INTO trade_history (symbol, entry_price, exit_price, lot_size, pnl, pnl_percent, entry_time, exit_time)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                       (symbol, pos['entry_price'], exit_price, pos['lot_size'], pnl, pnl_percent, pos['timestamp'], datetime.now().isoformat()))

        cursor.execute("DELETE FROM open_positions WHERE symbol = ?", (symbol,))
        conn.commit()
        conn.close()

        LoggerEngine.log_audit("CLOSE_POSITION", f"{symbol} | Çıkış: {exit_price} | PnL: {pnl:.2f} TL | Neden: {reason}")
        return True, {"pnl": pnl, "pnl_percent": pnl_percent}

    def manual_close(self, symbol, exit_price):
        return self.close_position(symbol, exit_price, reason="MANUAL_CLOSE")

    def get_trade_history(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trade_history ORDER BY id DESC")
        columns = [col[0] for col in cursor.description]
        history = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return history

    def is_in_cooloff_period(self, symbol):
        # 3 işlem günü bekleme süresi (Revenge Trading koruması)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT exit_time FROM trade_history WHERE symbol = ? ORDER BY id DESC LIMIT 1", (symbol,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return False

        exit_time = datetime.fromisoformat(row[0])
        days_passed = (datetime.now() - exit_time).days
        return days_passed < 3

    def is_blacklisted(self, symbol):
        # Dinamik Kara Liste Kontrolü (Analytics Engine ile entegre çalışır)
        try:
            with open("data/blacklist.json", "r") as f:
                blacklist = json.load(f)
            return symbol in blacklist
        except FileNotFoundError:
            return False

    def atomik_yedekle(self):
        # Elektrik kesintisine karşı veri bütünlüğü (Disaster Recovery)
        os.makedirs("backup", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backup/portfolio_{timestamp}.db"
        shutil.copy2(self.db_path, backup_path)
        logger.info(f"Veritabanı yedeklendi: {backup_path}")
        LoggerEngine.log_audit("DB_BACKUP", backup_path)
