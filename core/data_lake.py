import pandas as pd
import os
import sqlite3
from datetime import datetime
from config.config_manager import ConfigManager
from core.logger_engine import LoggerEngine

# "Veri Gölü" (Data Lake), zenginleştirilmiş verileri Machine Learning için arşivler.
# Parquet formatı, büyük verilerdeki (Big Data) hız avantajını sağlar.
# Doğru etiketlenmiş (Labeling) geçmiş veri, gelecekte "Hangi indikatör kombinasyonları kâr getiriyor?"
# sorusunu öğrenmesi için hayati önem taşır.

logger = LoggerEngine.get_system_logger()

class DataLake:
    def __init__(self, lake_dir="data_lake", db_path="data/portfolio.db"):
        self.lake_dir = lake_dir
        self.db_path = db_path
        os.makedirs(self.lake_dir, exist_ok=True)

    def archive_enriched_data(self, df: pd.DataFrame, symbol: str, signal_type: int = 0):
        """
        Günün sonunda (veya sinyal anında) DataFrame'i ML için arşivle.
        """
        try:
            if df is None or df.empty:
                return

            # Sadece son satırı (anlık snapshot) ekle veya tüm dataframe'i (isteğe bağlı)
            snapshot = df.iloc[[-1]].copy()
            snapshot['symbol'] = symbol
            snapshot['timestamp'] = datetime.now().isoformat()

            # Etiketleme (Labeling): İleride trade_history ile eşleştirilecek.
            # Şimdilik sinyal anındaki veriyi 'Pending' olarak kaydediyoruz.
            snapshot['Target'] = -1  # Bilinmiyor (Sonradan Reconciliation ile 1/0 yapılacak)

            filename = f"{self.lake_dir}/{symbol}_ML_Features.parquet"

            if os.path.exists(filename):
                # Mevcut Parquet'i oku ve ekle
                existing_df = pd.read_parquet(filename)
                combined_df = pd.concat([existing_df, snapshot], ignore_index=True)
                combined_df.to_parquet(filename, index=False)
            else:
                snapshot.to_parquet(filename, index=False)

            logger.info(f"ML Veri Gölü güncellendi: {filename}")

        except Exception as e:
            logger.error(f"Veri Gölü arşivleme hatası: {e}")

    def label_historical_trades(self):
        """
        Kapanan işlemleri (trade_history) okur ve ML_Features parquets'lerindeki
        'Target' sütununu Kâr (1) veya Zarar (0) olarak günceller.
        (Self-Learning ML altyapısı)
        """
        pass # Gelecekteki LSTM modelleri için ayrılmış altyapı
