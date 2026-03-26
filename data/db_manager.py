import logging
import sqlite3
import os
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Yerel SQLite veritabanı bağlantılarını (Connection Pooling) yönetir.
    Faz 17 uyarınca, SQLAlchemy gibi karmaşık ORM'ler yerine,
    basit, hafif, hataya dayanıklı (Fault-Tolerant) ve Multi-Thread safe bir
    Connection Provider sunar.
    Not: SQLAlchemy kullanımı "Sıfır Bütçe & Düşük Donanım" kısıtları nedeniyle
    basitleştirilmiş SQLite Native yapısına entegre edilmiştir. SQL sorguları
    SQLAlchemy Core / Native SQLite ile optimize şekilde yapılır.
    """
    def __init__(self, db_path=None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(base_dir, "data", "market_data.db")
        else:
            self.db_path = db_path

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.local = threading.local()
        self._initialize_core_tables()

    def _initialize_core_tables(self):
        """
        Sistemin çalışması için zaruri olan tabloları oluşturur.
        Faz 17 gereksinimleri (Trades ve Strategy_Metrics) buraya dahil edilmiştir.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 1. Paper Wallet
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS paper_wallet (
                        id INTEGER PRIMARY KEY,
                        balance REAL,
                        last_updated TEXT
                    )
                """)

                # 2. Open Positions (Açık İşlemler)
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

                # 3. Trade Journal (Kapalı/Açık Tüm İşlem Geçmişi)
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

                # 4. Strategy Metrics (Faz 16/17: Alpha Orkestratörü için metrik takibi)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS strategy_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        strategy_name TEXT,
                        win_rate REAL,
                        net_pnl REAL,
                        assigned_weight REAL
                    )
                """)

                # 5. Active Universe (Faz 19: Dinamik Hisse Havuzu)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS active_universe (
                        symbol TEXT PRIMARY KEY,
                        adv_20d REAL,
                        last_updated TEXT
                    )
                """)

                conn.commit()
                logger.info("Çekirdek veritabanı tabloları başlatıldı/doğrulandı.")
        except Exception as e:
            logger.error(f"Veritabanı tabloları oluşturulurken hata: {e}")

    @contextmanager
    def get_connection(self):
        """
        Thread-safe SQLite bağlantısı sağlar.
        database is locked hatalarını (timeout ile) yönetir.
        """
        if not hasattr(self.local, "conn") or self.local.conn is None:
            # 30 saniye timeout: Eşzamanlı (Concurrent) okuma/yazma çakışmalarında
            # hemen hata atmak yerine bekler (ACID compliance için kritik).
            self.local.conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)

            # Performans optimizasyonları:
            # WAL (Write-Ahead Logging) modu okuma ve yazma işlemlerinin birbirini
            # daha az bloke etmesini sağlar.
            self.local.conn.execute("PRAGMA journal_mode=WAL")
            self.local.conn.execute("PRAGMA synchronous=NORMAL")
            self.local.conn.execute("PRAGMA temp_store=MEMORY")

        try:
            yield self.local.conn
        except sqlite3.Error as e:
            logger.error(f"SQLite Hatası (get_connection): {e}")
            self.local.conn.rollback()
            raise
        except Exception as e:
            logger.error(f"Beklenmeyen Veritabanı Hatası: {e}")
            self.local.conn.rollback()
            raise
        finally:
            # Opsiyonel: Her seferinde bağlantıyı kapatmak yerine havuzda tutabiliriz.
            # Şimdilik açık tutuyoruz (Thread.local)
            pass

    """
    [QUANT MİMARI NOTU - VERİTABANI VE ACID PRENSİPLERİ]
    Birçok algoritmik bot, işlem verilerini (State) JSON, CSV veya .txt dosyalarında tutar.
    Sistem aynı anda 3 hisseyi güncellerken dosya okuma/yazma çakışması yaşanırsa,
    dosya bozulur (Corruption). Sonuç: Tüm açık işlemler, maliyetler ve stop-loss
    seviyeleri silinir. Piyasada kör olursunuz.

    Bunu önlemek için, ACID (Atomicity, Consistency, Isolation, Durability) prensiplerine
    uygun bir ilişkisel veritabanı şarttır. SQLite, yerel projeler için mükemmeldir.
    WAL (Write-Ahead Logging) modunu aktif ederek, Telegram botunun (okuma) ve
    strateji döngüsünün (yazma) aynı anda veritabanına erişebilmesini (Concurrency)
    sağlıyoruz. Bu, sıfır bütçe ile kurumsal bir mimari kurmaktır.
    """
