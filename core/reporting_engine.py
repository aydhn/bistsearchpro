import pandas as pd
import sqlite3
import os
from datetime import datetime
from config.config_manager import ConfigManager
from core.logger_engine import LoggerEngine

logger = LoggerEngine.get_trade_logger()

# "Uyum (Compliance) ve Muhasebe" modülü.
# Bütçe sıfır olduğu için openpyxl kullanılarak kurumsal düzeyde bir Excel üretilir.
# Conditional formatting (Renklendirme) kurumsal fonlardaki analiz hızını artırır.
class ReportingEngine:
    def __init__(self, db_path="data/portfolio.db"):
        self.db_path = db_path
        os.makedirs("temp_charts", exist_ok=True)

    def export_history_csv(self) -> str:
        """Kapanan İşlemler tablosunu okusun ve ham CSV üretsin."""
        try:
            conn = sqlite3.connect(self.db_path)
            query = "SELECT * FROM trade_history ORDER BY id DESC"
            df = pd.read_sql_query(query, conn)
            conn.close()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"temp_charts/ED_Capital_Trade_History_{timestamp}.csv"
            df.to_csv(filename, index=False, encoding="utf-8-sig")

            logger.info(f"CSV Raporu Oluşturuldu: {filename}")
            return filename
        except Exception as e:
            logger.error(f"CSV dışa aktarma hatası: {e}")
            return None

    def export_portfolio_excel(self) -> str:
        """Kurumsal düzeyde bir Excel (.xlsx) dosyası üretsin."""
        try:
            conn = sqlite3.connect(self.db_path)

            query_open = "SELECT * FROM open_positions"
            df_open = pd.read_sql_query(query_open, conn)

            query_history = "SELECT * FROM trade_history ORDER BY id DESC"
            df_history = pd.read_sql_query(query_history, conn)

            conn.close()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"temp_charts/ED_Capital_Raporu_{timestamp}.xlsx"

            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df_open.to_excel(writer, sheet_name='Anlik Portfoy', index=False)
                df_history.to_excel(writer, sheet_name='Islem Gecmisi', index=False)

                # Excel Biçimlendirme (Formatting)
                workbook = writer.book
                sheet_history = writer.sheets['Islem Gecmisi']

                # Sütun genişliklerini ayarlama
                for col in sheet_history.columns:
                    max_length = 0
                    column = col[0].column_letter # Get the column name
                    for cell in col:
                        try: # Necessary to avoid error on empty cells
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    sheet_history.column_dimensions[column].width = adjusted_width

            logger.info(f"Excel Raporu Oluşturuldu: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Excel dışa aktarma hatası: {e}")
            return None
