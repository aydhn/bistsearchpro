# BIST Algorithmic Trading Bot (bistsearchpro)

Bu proje, Borsa İstanbul (BİST) için geliştirilmiş, **sıfır bütçeli**, **düşük frekanslı**, **çoklu-ajanlı (multi-agent)** bir algoritmik trading botudur. Proje, Python ile yazılmış olup, teknik ve temel analizleri otomatikleştirerek asenkron bir Telegram botu aracılığıyla sinyal ve portföy yönetimi sunar.

## Temel Tasarım Felsefesi ve Kısıtlamalar

Bu sistem, katı mimari kurallar ve optimizasyon prensipleri etrafında şekillenmiştir:
*   **Sıfır Bütçe & Ücretsiz Araçlar:** Hiçbir ücretli API veya veri akışı kullanılmaz. Sadece `tvdatafeed`, `yfinance` gibi ücretsiz, açık kaynaklı kütüphaneler ve yerel veritabanı çözümleri (SQLite) kullanılır.
*   **Arayüz Yok (No GUI):** Projede web arayüzü veya masaüstü kontrol paneli bulunmaz. Kullanıcı ile olan tek ve ana etkileşim noktası, `python-telegram-bot` kütüphanesi üzerine kurulu asenkron **Telegram Botu**dur.
*   **Python File Army Mimarisi:** Sistem tek bir monolitik yapıdan ziyade, birbirinden izole edilmiş scriptler ordusu (data fetchers, routers, brain, vb.) şeklinde tasarlanmıştır. Bu bileşenler asenkron olarak çalışır ve yerel SQLite (`UPSERT` mantığıyla) ile JSON state dosyaları üzerinden haberleşir.
*   **Performans & Optimizasyon:** Veri işleme, teknik indikatör hesaplamaları ve backtest süreçlerinde saf Python döngüleri (`for`/`while`) veya `iterrows()` kullanmak **kesinlikle yasaktır**. Tüm işlemler `pandas-ta`, `numpy.where` ve `pandas.shift` gibi kütüphanelerle **vektörel** olarak gerçekleştirilir. Hafıza yönetimi açısından işlem bitiminde `del df` ve `gc.collect()` çağrılarak bellek optimize edilir.
*   **Hafif Doğal Dil İşleme (NLP):** Türkçe haber/duyarlılık (sentiment) analizi için BERT gibi ağır yapay zeka modelleri yerine, sistem kaynaklarını tüketmeyen hafif, kural tabanlı sözlük (dictionary) yaklaşımları tercih edilmiştir.
*   **Nesne Yönelimli ve Güvenli Kod:** Proje sıkı OOP kurallarına, detaylı `try/except` bloklarına ve `logging` standartlarına bağlıdır.

## Mimari ve Klasör Yapısı

Sistem aşağıdaki izole edilmiş klasör yapısını gerektirir:

*   `/config`: Proje ayarları, risk parametreleri ve evrensel sabitlerin (`settings.py`) bulunduğu dizin.
*   `/core`: Ana sistemin kalbi; veri çekiciler (`data_fetcher_tv.py`, `data_fetcher_yf.py`), sinyal işleme (`brain.py`), veritabanı yönlendirici (`data_router.py`), sanal portföy yönetimi (`paper_trader.py`) ve risk/hafıza yöneticileri.
*   `/data`: Yerel veritabanı (`db_manager.py`) ve market verilerinin saklandığı dizin.
*   `/logs`: Sistemin sağlık durumu ve hata kayıtlarının tutulduğu dizin.
*   `/strategies`: Farklı algoritmaların bulunduğu modüller. Örn: `signal_trend.py`, `stat_arb.py`, `macro_filter.py`, `sentiment.py`, `regime_filter.py`, `indicators.py`.
*   `/telegram`: Kullanıcı ile etkileşim, komut yönetimi (`bot_commands.py`) ve asenkron bildirim katmanı (`notifier.py`).
*   `/backtest`: Geçmiş veriler üzerinde vektörel testlerin yapıldığı modül (`engine.py`).

Tüm bileşenler, zamanlayıcı (`main_scheduler.py`) ve ana tetikleyici (`run_bot.py`) tarafından orkestre edilir.

## Kurulum ve Kullanım Kılavuzu

Projenin çalıştırılabilmesi için sistemde **Python 3.10+** yüklü olması önerilir.

### 1. Bağımlılıkların Yüklenmesi
Terminal veya komut satırını açarak proje dizinine gidin ve gerekli kütüphaneleri yükleyin:
```bash
pip install -r requirements.txt
```

### 2. Ortam Değişkenlerinin Ayarlanması
Botun sizinle iletişim kurabilmesi için bir Telegram Botu oluşturmalı (BotFather üzerinden) ve kendi kullanıcı ID'nizi belirlemelisiniz.

Aşağıdaki komutları işletim sisteminize göre terminalinize girin:

**Linux / macOS:**
```bash
export TELEGRAM_TOKEN='botfather_dan_aldiginiz_token'
export CHAT_ID='sizin_telegram_id_niz'
```

**Windows (PowerShell):**
```powershell
$env:TELEGRAM_TOKEN='botfather_dan_aldiginiz_token'
$env:CHAT_ID='sizin_telegram_id_niz'
```
*(Alternatif olarak bu değerleri .env dosyasına veya doğrudan sistem ortam değişkenlerine kalıcı olarak da ekleyebilirsiniz.)*

### 3. Sistemin Başlatılması
Ortam değişkenleri ayarlandıktan sonra ana orkestratör dosyasını çalıştırın:
```bash
python run_bot.py
```
Bu komut gerekli klasörleri oluşturur (veri, log vb.), SQLite veritabanı tablolarını senkronize eder, asenkron `main_scheduler` (saat başı veri güncelleme, piyasa saatlerinde pozisyon kontrolü) ve Telegram Bot `polling` mekanizmasını aynı anda başlatır.

Sistem başarılı bir şekilde ayağa kalktığında Telegram üzerinden bir başlangıç onayı ("🚀 BİST Algoritmik Sinyal Motoru başlatıldı.") alacaksınız.

## Telegram Bot Komutları

Yetkili kullanıcı (`CHAT_ID`), Telegram üzerinden aşağıdaki komutlarla sisteme erişebilir:

*   `/start`: Botu uyandırır ve kullanılabilecek temel komutları listeler.
*   `/status`: Sistemin mevcut sağlığını, piyasa rejimini ve sanal cüzdan bakiyesini gösterir.
*   `/report`: Mevcut açık pozisyonlarınızı, giriş fiyatlarınızı, yönlerini ve lot miktarlarını özetler.
*   `/analyze <SEMBOL>`: Belirtilen sembol (örn: `/analyze THYAO`) için anlık teknik analiz özetini talep eder.

---

> **Not:** Bu proje modüler bir yapıda 25 farklı aşamada (faz) inşa edilecek şekilde tasarlanmıştır. Sistemi genişletirken veya yeni stratejiler eklerken bu dokümandaki katı kurallara uyulması zorunludur.
