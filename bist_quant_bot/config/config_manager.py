import json
import os
import logging

class ConfigManager:
    """
    Sistemin tüm DNA'sını barındıran merkezi ayar yöneticisi.
    Kıdemli Yazılım Mimarı Notu: Hardcoding (Sabit değer atama) yazılım mimarisinin en büyük düşmanıdır.
    Separation of Concerns (Sorumlulukların Ayrılığı) prensibi gereği tüm parametreler dışarıdan,
    doğrulanarak (Validation) alınmalıdır. Canlı sistemlerde yanlış bir tip (örn: float yerine string)
    facialara yol açabilir. Bu yüzden burada sıkı bir tip kontrolü (Strict Type Checking) yapıyoruz.
    """
    _instance = None
    _config = None

    def __new__(cls, config_path="config/config.json"):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config(config_path)
        return cls._instance

    def _load_config(self, config_path):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Kritik Hata: Konfigürasyon dosyası bulunamadı: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            self._validate_config()
        except json.JSONDecodeError as e:
            raise ValueError(f"Kritik Hata: Konfigürasyon dosyası bozuk veya geçersiz JSON formatı! {e}")
        except Exception as e:
            raise Exception(f"Kritik Hata: Config yüklenirken beklenmeyen hata oluştu: {e}")

    def _validate_config(self):
        """
        Dinamik ayarların veri tiplerini ve sınırlarını doğrular.
        """
        try:
            # Tip Doğrulamaları (Validation)
            if not isinstance(self._config['trading_parameters']['MAX_RISK_PER_TRADE_PCT'], (int, float)):
                raise TypeError("MAX_RISK_PER_TRADE_PCT sayısal (float) olmalıdır.")
            if not isinstance(self._config['trading_parameters']['MAX_OPEN_POSITIONS'], int):
                raise TypeError("MAX_OPEN_POSITIONS tam sayı (int) olmalıdır.")
            if not isinstance(self._config['strategy_settings']['EMA_SHORT'], int):
                raise TypeError("EMA_SHORT tam sayı (int) olmalıdır.")

            # Mantıksal Sınır Doğrulamaları
            if self._config['trading_parameters']['MAX_RISK_PER_TRADE_PCT'] > 5.0:
                 logging.warning("Risk uyarısı: İşlem başına risk %5'ten büyük olmamalıdır! (%5 e çekildi)")
                 self._config['trading_parameters']['MAX_RISK_PER_TRADE_PCT'] = 5.0

        except KeyError as e:
            raise ValueError(f"Kritik Hata: Konfigürasyon dosyasında eksik anahtar var: {e}")

    @property
    def get(self):
        return self._config
