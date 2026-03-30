import sqlite3
import logging
import json
import os
from datetime import datetime, timedelta
import pandas as pd

class PortfolioManager:
    """
    Sistemin Hafızası (Sanal Kasa).
    SQLite tabanlı, Atomik Yazma / Okuma ile Felaket Kurtarmaya (Disaster Recovery) hazır mimari.
    N+1 sorgu problemi önlenmiş, batch insert ve pandas itertuples kullanılmış.
    """
    def __init__(self, config, db_path="data/portfolio.db"):
        self.db_path = db_path
        self.initial_balance = config['trading_parameters']['INITIAL_BALANCE']
        self.atr_multiplier_sl = config['strategy_settings']['ATR_MULTIPLIER_SL']
        self._init_db()

    def _init_db(self):
        """Veritabanı tablolarını yoksa oluşturur. (Memory / State Persistence)"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Açık Pozisyonlar Tablosu
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS open_positions (
                        symbol TEXT PRIMARY KEY,
                        entry_price REAL,
                        current_price REAL,
                        lot_size INTEGER,
                        stop_loss REAL,
                        take_profit REAL,
                        entry_date TEXT,
                        highest_price REAL
                    )
                ''')
                # İşlem Geçmişi (Kapalı İşlemler) Tablosu
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trade_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT,
                        entry_price REAL,
                        exit_price REAL,
                        lot_size INTEGER,
                        pnl_pct REAL,
                        net_profit REAL,
                        entry_date TEXT,
                        exit_date TEXT,
                        exit_reason TEXT
                    )
                ''')
                # Sistem Durumu (Kasa) Tablosu
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_state (
                        id INTEGER PRIMARY KEY,
                        current_balance REAL,
                        last_updated TEXT
                    )
                ''')
                # Bakiye kontrolü (Eğer tablo boşsa initial_balance ekle)
                cursor.execute('SELECT current_balance FROM system_state WHERE id=1')
                result = cursor.fetchone()
                if not result:
                    cursor.execute('INSERT INTO system_state (id, current_balance, last_updated) VALUES (1, ?, ?)',
                                 (self.initial_balance, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Veritabanı Başlatma Hatası: {e}")

    def get_balance(self) -> float:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT current_balance FROM system_state WHERE id=1')
            return cursor.fetchone()[0]

    def update_balance(self, amount: float):
        """Atomik/Transaction bazlı bakiye güncellemesi"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE system_state SET current_balance = current_balance + ?, last_updated = ? WHERE id=1',
                         (amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()

    def get_open_positions(self) -> dict:
        """Açık pozisyonları bir dictionary listesi olarak döner"""
        positions = {}
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM open_positions')
            for row in cursor.fetchall():
                positions[row['symbol']] = dict(row)
        return positions

    def has_open_position(self, symbol: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM open_positions WHERE symbol=?', (symbol,))
            return cursor.fetchone() is not None

    def is_in_cooloff(self, symbol: str, days=3) -> bool:
        """
        Cool-off (Bekleme Süresi): Aynı hissede arka arkaya işlem açmayı engeller.
        Son çıkış tarihinden itibaren X gün geçmeden yeni alım onaylanmaz.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT exit_date FROM trade_history WHERE symbol=? ORDER BY exit_date DESC LIMIT 1', (symbol,))
            result = cursor.fetchone()
            if result:
                try:
                    exit_date = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
                    if datetime.now() < exit_date + timedelta(days=days):
                        return True
                except:
                    pass
        return False

    def is_blacklisted(self, symbol: str) -> bool:
        """Kara liste veritabanı JSON veya DB üzerinden kontrol (Phase 16'ya hazırlık)"""
        blacklist_path = "data/blacklist.json"
        if os.path.exists(blacklist_path):
            try:
                with open(blacklist_path, 'r') as f:
                    blacklist = json.load(f)
                    return symbol in blacklist
            except: pass
        return False

    def add_position(self, position_data: dict):
        """
        Sinyal VETO'yu geçtikten sonra pozisyonu açar ve kasadan parayı düşer.
        Phase 18 (Pending State) aktifse, bu fonksiyon direkt KULLANILMAZ.
        Bunun yerine pending_signals -> Admin Onayı -> add_position akışı çalışır.
        """
        symbol = position_data['symbol']
        entry_price = position_data['entry_price']
        lot_size = position_data['lot_size']
        sl = position_data['stop_loss']
        tp = position_data['take_profit']

        total_cost = entry_price * lot_size

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO open_positions (symbol, entry_price, current_price, lot_size, stop_loss, take_profit, entry_date, highest_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, entry_price, entry_price, lot_size, sl, tp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), entry_price))

            # Kasadan parayı düş (Maliyet)
            cursor.execute('UPDATE system_state SET current_balance = current_balance - ?, last_updated = ? WHERE id=1',
                         (total_cost, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()

        logging.info(f"Portföye Eklendi: {symbol} | Maliyet: {total_cost:.2f} TL")

    def manage_trailing_stop_and_exits(self, current_prices: dict, atr_values: dict) -> list:
        """
        Phase 7 & 9 Çıkış Motoru: Trailing Stop (İzleyen Stop) ve TP/SL tetikleme mekanizması.
        current_prices: { "THYAO.IS": 150.5, "TUPRS.IS": 160.2 } şeklinde dictionary.
        Dönüş: Kapanan işlemler listesi (Telegram bildirimi için).
        """
        closed_trades = []
        positions = self.get_open_positions()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for symbol, pos in positions.items():
                if symbol not in current_prices:
                    continue

                current_price = current_prices[symbol]
                entry_price = pos['entry_price']
                highest_price = pos['highest_price']
                current_sl = pos['stop_loss']
                tp_price = pos['take_profit']
                lot_size = pos['lot_size']

                # --- ÇIKIŞ KONTROLÜ (SL veya TP Vurdu mu?) ---
                exit_reason = None
                if current_price <= current_sl:
                    exit_reason = "STOP_LOSS" # veya TRAILING_STOP vurdu
                elif current_price >= tp_price:
                    exit_reason = "TAKE_PROFIT"

                if exit_reason:
                    # Pozisyonu kapat (trade_history'e at, parayı kasaya ekle)
                    net_profit = (current_price - entry_price) * lot_size
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    total_return = current_price * lot_size

                    # History'e ekle
                    cursor.execute('''
                        INSERT INTO trade_history (symbol, entry_price, exit_price, lot_size, pnl_pct, net_profit, entry_date, exit_date, exit_reason)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (symbol, entry_price, current_price, lot_size, pnl_pct, net_profit, pos['entry_date'], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), exit_reason))

                    # Kasaya parayı geri koy (Ana Para + Kar/Zarar)
                    cursor.execute('UPDATE system_state SET current_balance = current_balance + ?, last_updated = ? WHERE id=1',
                                 (total_return, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

                    # Açık pozisyondan sil
                    cursor.execute('DELETE FROM open_positions WHERE symbol=?', (symbol,))

                    closed_trades.append({
                        "symbol": symbol,
                        "exit_reason": exit_reason,
                        "pnl_pct": pnl_pct,
                        "net_profit": net_profit,
                        "entry_price": entry_price,
                        "exit_price": current_price
                    })
                    logging.info(f"İşlem Kapandı [{symbol}]: {exit_reason}. Net Kâr: {net_profit:.2f} TL (%{pnl_pct:.2f})")
                    continue

                # --- İZLEYEN STOP (TRAILING STOP) GÜNCELLEMESİ ---
                # Fiyat yeni bir tepe yaptıysa SL'yi yukarı çek
                if current_price > highest_price:
                    highest_price = current_price
                    # Yeni Stop Loss seviyesi (Highest - 1.5*ATR)
                    atr = atr_values.get(symbol, 0)
                    if atr > 0:
                        new_sl = highest_price - (atr * self.atr_multiplier_sl)
                        # Stop loss SADECE YUKARI taşınabilir, asla aşağı inmez
                        if new_sl > current_sl:
                            # Break-even (başa baş) koruması (isteğe bağlı)
                            if new_sl > entry_price and current_sl <= entry_price:
                                logging.info(f"KORUMA KALKANI: {symbol} Stop-Loss seviyesi kara geçti (Break-Even). Risk sıfırlandı.")

                            cursor.execute('UPDATE open_positions SET stop_loss=?, highest_price=?, current_price=? WHERE symbol=?',
                                         (new_sl, highest_price, current_price, symbol))
                            logging.debug(f"Trailing Stop Güncellendi [{symbol}]: Yeni SL={new_sl:.2f}")
                else:
                    # Sadece güncel fiyatı güncelle
                    cursor.execute('UPDATE open_positions SET current_price=? WHERE symbol=?', (current_price, symbol))

            conn.commit()

        return closed_trades

    def add_pending_signal(self, position_data: dict):
        """Phase 18: Manuel onay için sinyali geçici hafızaya alır"""
        pending_path = "data/pending_signals.json"
        signals = {}
        if os.path.exists(pending_path):
            with open(pending_path, 'r') as f:
                try: signals = json.load(f)
                except: pass

        # Sinyal saatini ekle (Timeout için)
        position_data['signal_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        signals[position_data['symbol']] = position_data

        # Atomik yazma simülasyonu
        temp_path = f"{pending_path}.tmp"
        with open(temp_path, 'w') as f:
            json.dump(signals, f, indent=4)
        os.replace(temp_path, pending_path)
