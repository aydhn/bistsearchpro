# ED Capital - BIST Algorithmic Trading Bot (V1.0)

**Piyasalara Genel Bakış:** Borsa İstanbul (BIST) üzerinde kural tabanlı (Rule-Based) teknik analiz ve "Confluence" (Çoklu Doğrulama) mimarisiyle çalışan, insan onayı (Human-in-the-Loop) gerektiren yarı otonom bir fon yönetimi botudur.

## Katı Kurallarımız ve Sistem Mimarisi
* **Sıfır Bütçe:** Tamamen ücretsiz kütüphaneler (YFinance) ve araçlar kullanılır.
* **Scraping Yok:** BIST verileri doğrudan yapılandırılmış DataFrame'ler (OHLCV) olarak çekilir.
* **Donanım Tasarrufu:** UI/Dashboard (Streamlit vb.) yoktur. Görseller ve raporlar (`.xlsx`, `.csv`, `.png`) arka planda üretilip doğrudan Telegram üzerinden iletilir.
* **Paralel Optimizasyon:** Asenkron `ThreadPoolExecutor` ve `asyncio` ile CPU/RAM kullanımı optimize edilmiştir.
* **Makine Öğrenmesi (ML) Hazırlığı:** Sistemin işlediği veriler `.parquet` formatında **Data Lake** içerisine hedeflenmiş (Target) olarak arşivlenir.

## Kurulum
1. Python 3.10+ kurulu olduğundan emin olun.
2. Konsolu açıp projeye gidin ve bir sanal ortam oluşturup aktive edin.
3. `pip install -r requirements.txt` ile bağımlılıkları yükleyin.
4. `config/config.json` dosyasını kendi API bilgilerinizle (TELEGRAM_TOKEN ve ADMIN_CHAT_ID) doldurun.
5. Windows için `silent_runner.vbs` ile sessiz başlatabilir veya Linux için `./start_bot.sh` kullanabilirsiniz.

## Klasör Yapısı (Python Dosya Ordusu)
* `/config/`: Dinamik ayarlar (`config.json` ve `config_manager.py`).
* `/core/`: Sistemin beyin ve bel kemiği (Risk, Portföy, Sağlık Kontrolü, İndikatörler).
* `/strategies/`: İşlem üreten ve çoklu doğrulamayı yapan mantık çekirdekleri.
* `/telegram_bot/`: Asenkron ve Long-Polling yapıda interaktif haberleşme aracı.
* `/backtest/`: Olay tabanlı (Event-Driven) backtest ve Monte Carlo risk simülasyonları.
* `/data_lake/`: Makine öğrenmesi (ML) modelleri için `.parquet` arşiv dizini.
* `/logs/`: Hata ayıklama (`system.log`) ve değiştirilemez denetim izi (`audit_trail.log`).
* `/temp_charts/`: Geçici `.png` ve `.xlsx` dosyalarının barındığı alan. Otomatik temizlenir.

**Sorumluluk Reddi:** Bu yazılım sadece eğitim ve Ar-Ge amaçlıdır. Yatırım tavsiyesi içermez.
