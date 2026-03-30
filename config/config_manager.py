import json
import logging
from pathlib import Path

# ED Capital Kurumsal Şablonu ciddiyetinde, konfigürasyon doğrulamasının (Validation)
# canlı sistemlerdeki faciaları (Silent Failure) nasıl önlediğini gösteren yöneticidir.
# Hardcoding yapmamak (Separation of Concerns), yazılım mimarisinin sürdürülebilirliği için hayatidir.

class ConfigManager:
    _instance = None
    _config = {}

    def __new__(cls, config_path="config/config.json"):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config(config_path)
        return cls._instance

    def _load_config(self, config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
            self._validate_config()
        except FileNotFoundError:
            raise RuntimeError(f"Kritik Hata: Konfigürasyon dosyası bulunamadı: {config_path}")
        except json.JSONDecodeError:
            raise RuntimeError(f"Kritik Hata: Konfigürasyon dosyası bozuk (Geçersiz JSON): {config_path}")

    def _validate_config(self):
        # Tip ve Hata Doğrulaması (Validation)
        try:
            risk = float(self._config.get("trading_parameters", {}).get("MAX_RISK_PER_TRADE_PERCENT", 0))
            if risk <= 0 or risk > 10:
                raise ValueError("MAX_RISK_PER_TRADE_PERCENT 0-10 arasında olmalıdır.")

            polling = int(self._config.get("system_settings", {}).get("POLLING_INTERVAL_MINUTES", 0))
            if polling <= 0:
                raise ValueError("POLLING_INTERVAL_MINUTES pozitif bir tam sayı olmalıdır.")
        except ValueError as e:
            raise ValueError(f"Kritik Hata: Konfigürasyon tipi yanlış! Detay: {e}")

    @classmethod
    def get(cls, section, key=None):
        if not cls._instance:
            cls()
        if key:
            return cls._instance._config.get(section, {}).get(key)
        return cls._instance._config.get(section, {})
