import logging
import pandas as pd
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestClassifier
from data.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class JournalLearner:
    """
    Sistemin kârlı/zararlı işlemlerinden kendi kendine öğrenen (Self-Learning) yapısı.
    trade_journal veritabanından son N işlemi çeker.
    RSI, ATR, Kelly Lot gibi teknik/makro özellikleri 'X', işlemin PnL sonucunu 'Y' (1/0)
    olarak ayarlar ve RandomForest algoritması ile eğitip modeli (.pkl) olarak kaydeder.
    """
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

        # Modeli kaydetmek için klasör oluştur (örn: data/models)
        self.model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'models')
        os.makedirs(self.model_dir, exist_ok=True)

        self.model_path = os.path.join(self.model_dir, 'rf_predictor.pkl')
        self.model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=5)

    def retrain_model(self):
        """
        Her haftanın kapanışında veya belirli döngülerde tetiklenen model eğitim süreci.
        """
        logger.info("Yapay Zeka (Random Forest) eğitim süreci başlatılıyor...")

        try:
            with self.db.get_connection() as conn:
                # Sadece KAPALI ve PnL (Kâr/Zarar) netleşmiş işlemleri al
                query = "SELECT * FROM trade_journal WHERE status = 'CLOSED'"
                df = pd.read_sql_query(query, conn)

            if df.empty or len(df) < 50:
                logger.warning(f"Eğitim için yetersiz işlem sayısı ({len(df)}). Model güncellenmedi.")
                return False

            # Öznitelik Çıkarımı (Feature Engineering)
            # Zaman bilgilerinden günün saati veya haftanın günü gibi features çıkarılabilir.
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek

            # Kategorik verileri sayısal değerlere dönüştür (Encoding)
            df['is_bull_regime'] = (df['market_regime'] == 'BULL').astype(int)
            df['is_long_direction'] = (df['direction'] == 'BUY').astype(int)

            # Bağımsız değişkenler (X)
            features = ['rsi_value', 'atr_value', 'kelly_lot', 'hour', 'day_of_week', 'is_bull_regime', 'is_long_direction']

            # Eksik değerleri doldur (Imputation)
            X = df[features].fillna(0)

            # Etiketleme (Labeling - Y)
            # PnL > 0 ise kazançlı (1), aksi halde zararlı (0)
            y = (df['pnl'] > 0).astype(int)

            # Sınıf dengesizliği (class imbalance) varsa RF nispeten toleranslıdır,
            # ancak çok kötüyse smote uygulanabilir. Şimdilik temel model kuruyoruz.

            # Modeli eğit (fit)
            self.model.fit(X, y)

            # Modeli diske kaydet (.pkl)
            joblib.dump(self.model, self.model_path)

            logger.info(f"Model başarıyla eğitildi ve kaydedildi ({len(df)} işlem üzerinden).")
            return True

        except Exception as e:
            logger.error(f"Yapay zeka modeli eğitilirken hata oluştu: {e}")
            return False

    """
    [QUANT MİMARI NOTU - RANDOM FOREST (KARAR AĞACI) ÜSTÜNLÜĞÜ]
    Neden derin öğrenme (Neural Networks) değil de basit Karar Ağaçları?
    Finansal veriler gürültülüdür (Noisy) ve çoğu zaman lineer değildir.
    Ayrıca donanım limitlerimiz gereği yüksek CPU/GPU harcamaktan kaçınıyoruz.

    Rule-based (kural tabanlı) stratejiler, örneğin "RSI 30'da AL" der. Ancak bu
    kurallar zamanla körleşir. Belki RSI 30'dayken "Cuma günleri öğleden sonra"
    alınan hisseler genel olarak zararla kapatılıyordur. (Gizli Korelasyonlar)

    Random Forest, bu farklı feature'ları (RSI + Saat + Rejim) yüzlerce farklı
    ağaca bölüp "Bu işlemin kazanma ihtimali istatistiksel olarak nedir?"
    sorusuna cevap arar. Eğer bu model, mükemmel görünen bir teknik sinyalin
    kazanma ihtimalini geçmiş kayıplara dayanarak düşük görüyorsa (%55 altı),
    o işlem VETO edilir.
    """
