# ED CAPITAL - BIST Quant Bot (V1.0 Hybrid)
## Piyasalara Genel Bakış ve Mimari Teslimat Raporu

Bu proje, SPK Düzey 3 risk standartlarına sadık, Bill Benter istatistiksel dehası ve JP Morgan Fon Yöneticisi disiplini ile inşa edilmiş "Python Dosya Ordusu" mimarisidir. Sıfır bütçe ile 7/24 otonom çalışacak şekilde tasarlanmıştır. Auto-Execution (otomatik alım-satım) yerine **Human-in-the-Loop** (Döngüde İnsan) mimarisi kullanılarak slippage ve latency problemleri bypass edilmiştir.

### 🏛️ Mimari Harita (Directory Tree)
- **`config/`**: Sistemin DNA'sı. `config.json` ile tüm strateji, risk ve sistem ayarları tek merkezden yönetilir. Hardcoding kesinlikle yasaktır.
- **`core/`**: Orkestranın kalbi.
  - `universe.py`: Taranacak hisseleri yönetir.
  - `data_engine.py`: `yfinance` üzerinden asenkron OHLCV verisi çeker.
  - `indicators.py`: `pandas_ta` ile %100 vektörel hesaplamalar (EMA, RSI, MACD, ATR) ve Anomali Tespitleri (Locked Limit, ATR Spikes) yapar.
  - `strategy.py`: Çoklu doğrulama (Confluence) ile AL/BEKLE sinyalleri üretir.
  - `risk_manager.py`: Sabit kesir risk modeli, dinamik lot hesaplaması ve VETO mekanizması.
  - `portfolio_manager.py`: SQLite tabanlı, Atomik yazma özellikli sanal kasa. Trailing Stop (İzleyen Stop) motorunu barındırır.
  - `market_filter.py`: Makro rejimi (Risk-On / Risk-Off) ve Devre Kesici (Flash Crash) durumlarını XU100 üzerinden denetler.
  - `live_engine.py`: Akıllı Tarama (Smart Polling) ve Fail-Safe döngüsü ile 7/24 kesintisiz operasyon sağlar.
- **`backtest/`**: Geçmişi analiz eden simülatörler.
  - `backtest_engine.py`: Look-ahead bias engellenmiş olay güdümlü (event-driven) motor.
  - `optimizer.py`: Multiprocessing ile parametre optimizasyonu.
  - `analytics_engine.py`: Win-rate analizi ile Dinamik Kara Liste (Self-Healing) oluşturur.
  - `risk_modeling.py`: Monte Carlo simülasyonu ile Probability of Ruin hesaplar.
- **`telegram_bot/`**: Komuta Merkezi. Long-polling ile asenkron çift yönlü iletişim (`/durum`, `/al_onayla`). Headless `mplfinance` grafik çizimi (`visuals_engine.py`) ve Excel/CSV Uyum Raporlaması (`reporting_engine.py`).
- **`data_lake/`**: Makine Öğrenmesi (ML) hazırlığı. `data_lake.py`, zenginleştirilmiş verileri hedef etiketleriyle (Target) `.parquet` formatında sıkıştırarak gelecekteki LSTM/RandomForest modelleri için arşivler.
- **`scripts/`**: Çapraz platform başlatıcılar (`start_bot.bat`, `silent_runner.vbs`, `start_bot.sh`).
- **`health_check.py`**: Uçuş Öncesi Kontrol. Config, I/O ve Network testlerinden geçemeyen sistemi başlatmayarak faciaları önler.

### 🚀 Kurulum (Windows / WSL)
1. Python 3.10+ kurulu olduğundan emin olun.
2. `pip install -r requirements.txt` komutuyla bağımlılıkları yükleyin.
3. `config/config.json` dosyasını açıp Telegram Token ve Admin Chat ID bilgilerinizi girin.
4. `python run_bot.py` (veya `scripts/start_bot.bat`) ile sistemi Savaş Moduna (Risk-On) alın.

Mimarimiz emrinize amadedir. Karlı ve disiplinli piyasalar dileriz.
