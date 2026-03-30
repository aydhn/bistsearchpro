import pandas as pd
import os
import logging

class DataLakeEngine:
    """
    ML Feature Engineering Arşivi (Phase 25 - Veri Gölü).
    Büyük veri (Big Data) hızı ve sıkıştırması için .parquet formatı kullanır.
    İndikatörlerle dolu DataFrame'i alıp gelecekteki Random Forest/LSTM modelleri için arşivler.
    """
    def __init__(self, lake_dir="data_lake"):
        self.lake_dir = lake_dir
        os.makedirs(self.lake_dir, exist_ok=True)

    def archive_features(self, symbol: str, df: pd.DataFrame, target_label=None):
        """
        Sinyal üretilen anki OHLCV + İndikatörleri Parquet olarak kaydeder.
        Eğer işlem kârla kapanırsa (Win) daha sonra Target=1 olarak etiketlenebilir.
        """
        try:
            if df is None or df.empty: return

            # Yalnızca son satırı (sinyal anını) veya tüm df'i arşivle (ML için tüm df değerlidir)
            archive_df = df.copy()

            # Etiketleme (Labeling) hazırlığı
            if target_label is not None:
                archive_df['Target'] = target_label
            else:
                archive_df['Target'] = -1 # Bilinmiyor / Pending

            file_path = os.path.join(self.lake_dir, f"{symbol}_features.parquet")

            # Dosya varsa üstüne ekle (Append) - Parquet'de doğrudan append zordur,
            # Genelde klasör bazlı partisyonlama (partitioning) yapılır.
            # Basitlik için pandas append simülasyonu:
            if os.path.exists(file_path):
                existing_df = pd.read_parquet(file_path)
                combined_df = pd.concat([existing_df, archive_df]).drop_duplicates()
                combined_df.to_parquet(file_path, index=False, engine='pyarrow', compression='snappy')
            else:
                archive_df.to_parquet(file_path, index=False, engine='pyarrow', compression='snappy')

            logging.debug(f"Veri Gölüne Eklendi (Parquet): {symbol}")
        except Exception as e:
            logging.error(f"Data Lake Arşiv Hatası ({symbol}): {e}")
