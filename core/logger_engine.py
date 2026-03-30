import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
import hashlib
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.config_manager import ConfigManager

# Kurumsal seviyede bir kayıt sistemi. RotatingFileHandler mantığını seçtik çünkü
# yıllar boyunca birikecek logların sabit diski doldurup sistemi çökertmesini (No space left on device) engellemek istiyoruz.
# Audit Trail (Denetim İzi), kurumsal uyum standartlarındaki manipülasyonları tespit etmek için kriptografik hash ile mühürlenir.

os.makedirs('logs', exist_ok=True)

class LoggerEngine:
    _system_logger = None
    _trade_logger = None
    _audit_logger = None
    _previous_hash = "GENESIS"

    @classmethod
    def get_system_logger(cls):
        if not cls._system_logger:
            log_level_str = ConfigManager.get("system_settings", "LOG_LEVEL") or "INFO"
            log_level = getattr(logging, log_level_str.upper(), logging.INFO)

            cls._system_logger = logging.getLogger("SYSTEM")
            cls._system_logger.setLevel(log_level)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

            # RotatingFileHandler: 5MB dosya boyutu, maksimum 5 yedek
            file_handler = RotatingFileHandler('logs/system.log', maxBytes=5*1024*1024, backupCount=5, encoding="utf-8")
            file_handler.setFormatter(formatter)
            cls._system_logger.addHandler(file_handler)

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            cls._system_logger.addHandler(console_handler)
        return cls._system_logger

    @classmethod
    def get_trade_logger(cls):
        if not cls._trade_logger:
            cls._trade_logger = logging.getLogger("TRADE")
            cls._trade_logger.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

            file_handler = RotatingFileHandler('logs/trade.log', maxBytes=10*1024*1024, backupCount=10, encoding="utf-8")
            file_handler.setFormatter(formatter)
            cls._trade_logger.addHandler(file_handler)
        return cls._trade_logger

    @classmethod
    def log_audit(cls, action, details):
        """Kriptografik zincirleme (Hash Chaining) ile Değiştirilemez Denetim İzi (Immutable Audit Log)"""
        if not cls._audit_logger:
            cls._audit_logger = logging.getLogger("AUDIT")
            cls._audit_logger.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(message)s')
            file_handler = logging.FileHandler('logs/audit_trail.log', encoding="utf-8")
            file_handler.setFormatter(formatter)
            cls._audit_logger.addHandler(file_handler)

        timestamp = datetime.now().isoformat()
        raw_string = f"{cls._previous_hash}|{timestamp}|{action}|{details}"
        current_hash = hashlib.sha256(raw_string.encode('utf-8')).hexdigest()

        log_entry = f"HASH: {current_hash} | PREV: {cls._previous_hash} | TS: {timestamp} | ACTION: {action} | DET: {details}"
        cls._audit_logger.info(log_entry)
        cls._previous_hash = current_hash
