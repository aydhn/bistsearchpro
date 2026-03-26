import logging
import pandas as pd
import numpy as np
import os
import joblib

logger = logging.getLogger(__name__)

class MLPredictor:
    """
    Eğitilmiş Yapay Zeka (Random Forest) modelini kullanarak anlık gelen
    strateji sinyallerinin kârlı sonuçlanma ihtimalini (Probability of Success) hesaplar.

    Katı Kural: Eğer yapay zeka bu sinyalin başarılı olma ihtimalini %55'in altında görüyorsa,
    strateji ne kadar mükemmel görünürse görünsün sinyali İPTAL EDER (VETO).
    """
    def __init__(self):
        self.model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'models')
        self.model_path = os.path.join(self.model_dir, 'rf_predictor.pkl')
        self.model = None
        self._load_model()

    def _load_model(self):
        """
        Kaydedilmiş .pkl modelini diske/RAM'e yükler.
        Zarif Hizmet Kaybı (Graceful Degradation): Model yoksa veya bozuksa,
        sistem çökmez, sadece ML onayı devre dışı bırakılır.
        """
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                logger.info("Yapay Zeka (ML) Modeli başarıyla yüklendi. %55+ Kâr Olasılığı filtresi aktif.")
            except Exception as e:
                logger.error(f"ML Modeli yüklenirken hata oluştu: {e}")
                self.model = None
        else:
            logger.warning("Eğitilmiş ML Modeli bulunamadı. Yeterli işlem (min 50) yapılana kadar ML filtresi devre dışı kalacaktır.")

    def evaluate_signal(self, features: dict) -> tuple[bool, float]:
        """
        Gelen anlık piyasa koşullarını (features) modele sorar ve kazanma olasılığını döndürür.

        Args:
            features (dict): {'rsi_value': 30.5, 'atr_value': 2.1, 'kelly_lot': 0.02,
                              'hour': 14, 'day_of_week': 2, 'is_bull_regime': 1, 'is_long_direction': 1}

        Returns:
            (is_approved, probability): (Onaylandı mı (bool), Kazanma İhtimali (float))
        """
        if self.model is None:
            # Zarif Hizmet Kaybı: Model yoksa işlemlere izin ver ama prob=0.0 dön (ML devrede değil anlamında)
            # Or perhaps return 0.50 (neutral) to allow the trade to pass the ML filter check,
            # but we'll return True to not block standard TA strategies until we have enough data to train.
            logger.debug("[⚠️ UYARI] ML Modeli devre dışı. Sinyaller yalnızca istatistiksel kurallarla üretiliyor.")
            return True, 0.0

        try:
            # Modeli eğitirken kullandığımız feature sırasına dikkat etmeliyiz:
            # ['rsi_value', 'atr_value', 'kelly_lot', 'hour', 'day_of_week', 'is_bull_regime', 'is_long_direction']
            X_input = pd.DataFrame([{
                'rsi_value': features.get('rsi_value', 50.0),
                'atr_value': features.get('atr_value', 1.0),
                'kelly_lot': features.get('kelly_lot', 0.01),
                'hour': features.get('hour', 10),
                'day_of_week': features.get('day_of_week', 0),
                'is_bull_regime': features.get('is_bull_regime', 1),
                'is_long_direction': features.get('is_long_direction', 1)
            }])

            # Sınıf 1 (Kazanma) olasılığını al
            prob = self.model.predict_proba(X_input)[0][1] * 100.0

            # %55 Kuralı
            if prob >= 55.0:
                logger.info(f"🤖 ML ONAYI: İşlemin başarılı olma ihtimali: %{prob:.2f} (Eşik: %55). Sinyal GÜVENLİ.")
                return True, prob
            else:
                logger.warning(f"🤖 ML REDDİ (VETO): İşlemin başarılı olma ihtimali: %{prob:.2f} (Eşik: %55). Sinyal İPTAL EDİLDİ.")
                return False, prob

        except Exception as e:
            logger.error(f"ML Predictor sinyal değerlendirme hatası: {e}")
            # Hata anında Graceful Degradation: İşlemi engelleme ama uyar.
            return True, 0.0
