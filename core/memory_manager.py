import gc
import functools
import logging
import inspect
import pandas as pd

logger = logging.getLogger(__name__)

def optimize_memory(func):
    """
    Düşük kapasiteli bir PC'de bellek sızıntılarını (memory leaks) önlemek için
    kullanılan dekoratör sınıf/fonksiyon. Veritabanından çekilen büyük Pandas
    DataFrame'leri ile işlem bittikten sonra Python çöp toplayıcısını (Garbage Collector)
    zorla çalıştırır.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # İşlevi çalıştır
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Bellek yönetimi: Yerel değişkenleri temizle (özellikle DataFrame'leri)
            frame = inspect.currentframe()
            try:
                # Wrapper'ın içine girip çalıştırılan fonksiyonun yerel kapsamına erişmek
                # oldukça zordur, ancak garbage collector'u açıkça çağırmak bile
                # büyük nesnelerin (fonksiyon döndükten sonra referanssız kalanlar)
                # silinmesini hızlandırır.

                # 'del df' komutunu spesifik bir fonksiyona dışarıdan uygulayamayacağımız için,
                # Python gc.collect() ile genel bir temizlik yapıyoruz.
                # Daha iyi bir yaklaşım: Büyük DataFrame'leri kullanan fonksiyonların
                # kendi içlerinde del df yapmasıdır.
                pass
            finally:
                del frame

            collected = gc.collect()
            logger.debug(f"Memory optimization triggered by {func.__name__}. Collected {collected} unreachable objects.")

    return wrapper

# API Bağlantı Havuzlarını (Connection Pools) temizleme rehberi:
# requests kullanan yerlerde (örn: FundamentalScraper) her requests.get() çağrısından sonra
# bağlantıların açık kalmasını önlemek için bir session nesnesi kullanılması
# veya `with requests.get(...) as response:` yapısı önerilir.

