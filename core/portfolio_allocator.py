import logging
from core.correlation_engine import CorrelationEngine
from data.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class PortfolioAllocator:
    """
    Stratejik Varlık Tahsisi Yöneticisi (Strategic Asset Allocation).
    Kağıt Üzerinde Ticaret (Paper Trading) modülüyle veya DB ile entegre çalışarak
    portföydeki hisseleri ve oranlarını takip eder.
    Ayrıca yeni gelen "AL" sinyallerini yüksek korelasyon (%80+) sebebiyle REDDEDEBİLİR.
    """
    def __init__(self, db_manager: DatabaseManager, correlation_engine: CorrelationEngine):
        self.db = db_manager
        self.correlation_engine = correlation_engine

    def get_open_symbols(self) -> list:
        """
        O an "Açık" (Open) olan, yani daha önce AL sinyali gelmiş ve
        henüz Satılmamış/Stop olmamış hisselerin listesini döndürür.
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT symbol FROM open_positions")
                rows = cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Portfolio Allocator açık sembolleri okuma hatası: {e}")
            return []

    def validate_allocation(self, new_symbol: str) -> bool:
        """
        strategy.py yeni bir hisse için "AL" sinyali (ve ML'den onay) ürettiğinde devreye girer.
        Yeni hisse, halihazırda portföyde bulunan aktif hisselerden herhangi biriyle
        +%80 üzeri korelasyona sahipse sinyali REDDEDER.
        """
        open_symbols = self.get_open_symbols()

        # Portföy boşsa direkt onay ver
        if not open_symbols:
            return True

        highly_correlated_symbols = self.correlation_engine.get_highly_correlated_symbols(new_symbol)

        if not highly_correlated_symbols:
            # Korelasyon verisi yoksa defansif olarak geçmesine izin veriyoruz (veya reddedilebilir)
            return True

        # Açık pozisyonlardaki herhangi bir hisse, yeni sembolle %80'den fazla korele mi?
        for open_sym in open_symbols:
            if open_sym in highly_correlated_symbols:
                logger.warning(f"⚠️ PORTFÖY REDDİ: {new_symbol}, portföydeki {open_sym} ile yüksek korelasyonlu (> %80). İşlem iptal edildi.")
                return False

        # Hiçbir açık pozisyonla yüksek korelasyonu yoksa onaylanır
        logger.info(f"✅ PORTFÖY ONAYI: {new_symbol} sektörel çeşitlilik sağlıyor.")
        return True

    def get_allocation_report(self, current_balance: float) -> str:
        """
        Telegram raporunun en altına eklenecek "Stratejik Varlık Tahsisi" metnini oluşturur.
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT symbol, entry_price, lot_size FROM open_positions")
                rows = cursor.fetchall()

            invested_amount = 0.0
            for row in rows:
                entry_price = row[1]
                lot_size = row[2]
                invested_amount += (entry_price * lot_size)

            total_equity = current_balance + invested_amount

            if total_equity > 0:
                cash_pct = (current_balance / total_equity) * 100.0
                invested_pct = (invested_amount / total_equity) * 100.0
            else:
                cash_pct = 100.0
                invested_pct = 0.0

            return f"Stratejik Varlık Tahsisi: %{invested_pct:.1f} Hisse, %{cash_pct:.1f} Nakit"

        except Exception as e:
            logger.error(f"Portfolio Allocator rapor oluşturma hatası: {e}")
            return "Stratejik Varlık Tahsisi: Hesaplanamadı"
