import pandas as pd
import sqlite3
import os
import logging
import uuid

class ReportingEngine:
    """
    Portföy Muhasebesi ve Gelişmiş Excel/CSV Raporlama (Phase 20).
    Uyum (Compliance) gereksinimleri için işlem geçmişini profesyonel dışa aktarır.
    Bütçe sıfır olduğu için açık kaynak xlsxwriter/openpyxl kullanılır.
    """
    def __init__(self, db_path="data/portfolio.db", temp_dir="temp_charts"):
        self.db_path = db_path
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)

    def export_history_csv(self) -> str:
        """Kapanan işlemleri ham CSV olarak üretir."""
        if not os.path.exists(self.db_path): return None
        file_path = os.path.join(self.temp_dir, f"ED_Capital_TradeHistory_{uuid.uuid4().hex[:6]}.csv")
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query("SELECT * FROM trade_history", conn)
            df.to_csv(file_path, index=False, encoding='utf-8-sig') # Excel Türkçe karakter uyumu için utf-8-sig
            return file_path
        except Exception as e:
            logging.error(f"CSV Rapor Hatası: {e}")
            return None

    def export_portfolio_excel(self) -> str:
        """
        Açık ve Kapalı işlemleri iki ayrı Sheet halinde profesyonel Excel (xlsx) üretir.
        Kıdemli Quant Notu: openpyxl ile condition formatting (renklendirme) analizi hızlandırır.
        """
        if not os.path.exists(self.db_path): return None
        file_path = os.path.join(self.temp_dir, f"ED_Capital_Portfolio_{uuid.uuid4().hex[:6]}.xlsx")

        try:
            with sqlite3.connect(self.db_path) as conn:
                df_open = pd.read_sql_query("SELECT * FROM open_positions", conn)
                df_history = pd.read_sql_query("SELECT * FROM trade_history", conn)

            # ExcelWriter objesi yarat
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df_open.to_excel(writer, sheet_name="Anlık Portföy", index=False)
                df_history.to_excel(writer, sheet_name="İşlem Geçmişi", index=False)

                # Açık kaynak openpyxl ile basit biçimlendirme eklenebilir
                # (Zaman/kod karmaşası için pandas tabanlı export yeterlidir)

            return file_path
        except Exception as e:
            logging.error(f"Excel Rapor Hatası: {e}")
            return None
