import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger():
    """
    Sistemin tüm log kayıtlarını konsola ve logs/bot.log dosyasına yazar.
    RotatingFileHandler ile log dosyası 5MB'ı aştığında otomatik yedeklenip temizlenir.
    Sistemin uptime takibi ve hataların geriye dönük incelenmesi için kritiktir.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Eğer logger önceden ayarlandıysa (örn. script yeniden çalıştırılırken)
    # birden fazla handler eklenmemesi için temizle
    if logger.hasHandlers():
        logger.handlers.clear()

    # Log formatı: Tarih - Modül - Seviye - Mesaj
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. Konsol Çıktısı (Console Handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. Dosya Çıktısı (File Handler - Rotating, 5MB max, 3 backup)
    # Log dizininin var olduğundan emin ol
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'bot.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5*1024*1024, # 5 MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info("Profesyonel loglama modülü (RotatingFileHandler) başarıyla başlatıldı.")
    return logger
