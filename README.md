# 📈 BIST Quant Alpha - Kurumsal Sinyal ve Risk Yönetim Mimarisi

BIST Quant Alpha, Borsa İstanbul (BİST) için geliştirilmiş, yüksek frekanslı ticaret (HFT) **olmayan**, aksine "High Win-Rate" odaklı, tamamen **Sıfır Bütçe** ve yerel kaynaklarla çalışan devasa bir algoritmik sinyal ve portföy yönetim ekosistemidir.

Sistem, yapay zeka (Makine Öğrenimi), makro veri analizleri, istatistiksel sapma filtreleri ve çoklu zaman dilimi onaylarıyla harmanlanmış profesyonel bir "Python Dosya Ordusu" mimarisine sahiptir. Piyasada kendi kendine karar verebilir, gelişmiş risk yönetimi uygular ve tüm süreçleri asenkron Telegram botu üzerinden bir fon yöneticisi titizliğiyle raporlar.

---

## 📂 Mimari Klasör Ağacı (Directory Tree)

Sistemimiz 21 fazlık modüler bir yapıda, Clean Code ve SOLID prensiplerine göre inşa edilmiştir:

```text
├── core/
│   ├── alpha_orchestrator.py    # Çoklu strateji ağırlıklarını belirler (Capital Rotation)
│   ├── correlation_engine.py    # Sektörel riskleri önleyen Pearson Korelasyon Matrisi
│   ├── data_fetcher_yf.py       # yfinance tabanlı, rate-limit korumalı ana veri çekici
│   ├── edge_case_handler.py     # Tavan/Taban ve hacim anomalisi engelleyici (BİST Filtresi)
│   ├── error_manager.py         # Graceful Degradation ve Exponential Backoff hata yöneticisi
│   ├── journal_learner.py       # Random Forest tabanlı makine öğrenimi eğitim motoru
│   ├── logger.py                # RotatingFileHandler kullanan profesyonel sistem kayıtçısı
│   ├── macro_data.py            # VIX, USDTRY ve Hurst Exponent gibi makro verileri çeker
│   ├── ml_predictor.py          # %55 Kâr İhtimali (Probability of Success) onayı veren ML filtresi
│   ├── mtf_engine.py            # "Büyük dalgaya sörf yapılmaz" - Çoklu Zaman Dilimi Onaylayıcısı
│   ├── paper_trader.py          # Sanal portföy PnL takipçisi ve pozisyon yöneticisi
│   ├── parameter_optimizer.py   # Calmar Rasyosu hedefli Randomized Search hiperparametre motoru
│   ├── portfolio_allocator.py   # Aynı anda %80+ korele işlemleri önleyen Portföy Yöneticisi
│   ├── position_sizer.py        # Kısmi Kelly (Half-Kelly) tabanlı dinamik lot hesaplayıcı
│   ├── risk_manager.py          # ATR tabanlı Trailing Stop, Breakeven ve Time-Stop yöneticisi
│   ├── state_recovery.py        # Crash Recovery: Elektrik kesintilerinde AÇIK işlemleri geri yükler
│   ├── trade_journal.py         # Tüm kararların SQLite DB'ye hukuki izlenebilirlikle kaydedilmesi
│   └── universe.py              # ADV İlk 40 hissesini seçen, zombi/gap tahtaları eleyen modül
│
├── strategies/
│   ├── cointegration_engine.py  # Engle-Granger testiyle eşbütünleşik hisse çiftleri arar
│   ├── indicators.py            # pandas-ta tabanlı hızlı vektörel indikatör kütüphanesi
│   ├── pairs_strategy.py        # Z-Skoru ile çalışan Göreceli Değer (Long-Only Stat Arb)
│   ├── regime_filter.py         # XU100 SMA200 tabanlı Boğa/Ayı (Market Regime) filtresi
│   └── strategy_factory.py      # Mean Reversion, Trend Following ve Volatility Breakout fabrikası
│
├── backtest/
│   ├── advanced_backtester.py   # Row-by-Row Tick simülasyonlu, olay yönlendirmeli backtest
│   ├── engine.py                # Vektörel hızlı backtest motoru
│   ├── execution_simulator.py   # Dinamik Slippage (Kayma) ve %0.04 Komisyon Simülasyonu
│   └── monte_carlo.py           # 10.000 Evrenli Monte Carlo İflas Olasılığı (Probability of Ruin) Testi
│
├── telegram_bot/
│   ├── bot_commands.py          # Uzaktan Komuta (/durum, /rapor, /durdur, /baslat) dinleyicisi
│   └── notifier.py              # Asenkron Telegram bildirim (Signal ve Alert) motoru
│
├── data/
│   ├── db_manager.py            # SQLite Veritabanı Connection Pooling ve Table Setup
│   └── models/                  # Eğitilmiş .pkl Yapay Zeka modellerinin kaydedildiği klasör
│
├── dashboard.py                 # Streamlit tabanlı, read-only Görsel Komuta Merkezi (GUI)
├── main_scheduler.py            # Zamanlanmış görevlerin (schedule) yürütüldüğü tetikleyici
├── run_bot.py                   # Asyncio ile Telegram ve Scheduler'ı paralel başlatan ana script
├── start_bot.bat                # Windows için tek tıkla Bot + Dashboard başlatıcı
└── requirements.txt             # Sistem bağımlılıkları listesi
```

---

## ⚙️ Kurulum ve Başlatma (Prerequisites & Installation)

**Sistem Gereksinimleri:**
- Python 3.10 veya üzeri
- Ortalama bir İşlemci (CPU) ve kablolu internet
- Borsa İstanbul (BİST) işlem saatlerinde bilgisayarın açık kalması önerilir

### 1. Ortamın Hazırlanması
Projeyi indirdikten sonra terminal üzerinden proje kök dizinine gidin ve gerekli kütüphaneleri yükleyin:
```bash
pip install -r requirements.txt
```

### 2. Çevresel Değişkenler (Environment Variables)
Botun size mesaj atabilmesi ve sizin dışınızdaki kullanıcıları reddetmesi için `TELEGRAM_TOKEN` ve `CHAT_ID` ayarlanmalıdır. BotFather üzerinden botunuzu oluşturup tokenınızı alın.

**Linux / macOS:**
```bash
export TELEGRAM_TOKEN='BOT_TOKENINIZ'
export CHAT_ID='TELEGRAM_ID_NIZ'
```

**Windows (PowerShell):**
```powershell
$env:TELEGRAM_TOKEN='BOT_TOKENINIZ'
$env:CHAT_ID='TELEGRAM_ID_NIZ'
```

### 3. Sistemin Başlatılması
Windows kullanıcıları doğrudan proje dizinindeki **`start_bot.bat`** dosyasına çift tıklayarak sistemi tam kapasite ayağa kaldırabilir. Bu dosya, arka planda ana bot döngüsünü başlatırken, eşzamanlı olarak tarayıcınızda Streamlit Komuta Merkezi'ni açacaktır.

Manuel başlatmak için:
```bash
python run_bot.py
```
Ayrıca, başka bir terminal açarak Dashboard'u da manuel çalıştırabilirsiniz:
```bash
streamlit run dashboard.py
```

---

## 📱 Telegram Komuta Merkezi Kullanımı

Sistem sadece pasif bir sinyal göndericisi değildir. Telegram üzerinden botunuza aşağıdaki komutları göndererek otonom sisteme yön verebilirsiniz:

| Komut | Açıklama |
|---|---|
| `/start` | Sistemin karşılama mesajı ve yetkili olduğunuzun doğrulanması. |
| `/durum` | Sistemin anlık Market Rejimini (Boğa/Ayı), çalışma süresini (Uptime) ve tarama modunu (Aktif/Uyku) özetler. |
| `/rapor` | Sanal (Paper Trading) cüzdan bakiyesini, açık hisse oranını ve gerçekleşmiş PnL (Kâr/Zarar) toplamını sunar. |
| `/durdur` | **(Kill Switch)** Panik anlarında (Örn: ani bir Flash Crash) sinyal aramayı ve işlem girmeyi acil olarak durdurur. |
| `/baslat` | Kill Switch ile uyku moduna alınmış (Paused) sistemi tekrar aktif tarama moduna geçirir. |

---

## 🛡️ Kurumsal Uyum ve Denetim (Compliance & Audit Trail)

Bu mimari; amatör CSV loglamalarından uzak, `data/db_manager.py` üzerinden SQLite ilişkisel veritabanına ACID prensipleriyle (Atomicity, Consistency, Isolation, Durability) bağlıdır. Sistemdeki her sinyal kararı, ATR değerleri, Kelly fraksiyonu, Makro durumlar ve Makine Öğrenimi (ML) onayı `trade_journal` tablosuna zaman damgalı olarak işlenir.

Eğer sunucu veya bilgisayar aniden kapanırsa (Elektrik kesintisi vb.), `State Recovery` modülü bir sonraki açılışta işlemleri doğrudan veritabanından geri yükler ve bir işlem "Çevrimdışıyken Stop-Loss yemişse" saniyesinde kritik uyarı atar.

---

## ⚠️ Yasal Uyarı (Disclaimer)

**RİSK BİLDİRİMİ:** Bu yazılım tamamen araştırma, eğitim ve simülasyon amacıyla kodlanmıştır. **Hiçbir şekilde yatırım danışmanlığı veya al-sat tavsiyesi içermez.** Borsa İstanbul (BİST) gibi yüksek volatilite barındıran piyasalardaki mikro yapı riskleri (Devre Kesiciler, Tavan/Taban serileri, anlık likidite kuruması vb.) yazılım tarafından simüle edilmeye çalışılsa da, gerçek dünya sonuçlarıyla farklılık gösterebilir. Sanal ve gerçek portföy işlemlerinizden doğacak kâr ve zararlar **tamamen yatırımcının kendi sorumluluğundadır.**

*Yazılımın üretmiş olduğu Kelly Kriteri hesaplamaları, Z-Skorları ve Makine Öğrenimi tahminleri bir yatırım garantisi (holy grail) değil, istatistiksel birer varsayımdan ibarettir.*
