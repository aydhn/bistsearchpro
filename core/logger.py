import logging
from logging.handlers import RotatingFileHandler
import os
from config.settings import config

def setup_logger():
    """
    Sistemin tüm loglama altyapısını kurar.
    Konsola (stdout) ve bot_system.log dosyasına döner (rotating) dosya mantığıyla yazar.
    Maksimum 5 MB x 3 Yedek.
    """
    if not os.path.exists(config.LOG_DIR):
        os.makedirs(config.LOG_DIR)

    log_file = os.path.join(config.LOG_DIR, "bot_system.log")

    # Root logger yapılandırması
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG) # En detaylı seviyeyi kök olarak alıp handler'larda kırpıyoruz

    # Format
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. Rotating File Handler (Sadece INFO ve üzeri logları dosyaya kaydet)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024, # 5 MB
        backupCount=3,            # 3 yedek
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Root logger'da eski handler'ları temizle (tekrar çağrılma ihtimaline karşı)
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(file_handler)

    # 2. Console Handler (Tüm seviyeler - Geliştirme/Takip için)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

logger = setup_logger()
