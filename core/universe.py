import logging
import os
import pandas as pd
from data.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class SymbolUniverse:
    """
    Dinamik Havuz Seçici (Dynamic Universe Selection) ve Likidite Filtresi.
    BIST100'ün tüm kodlarının bulunduğu bir dosyadan veya listeden okuyup,
    ortalama günlük hacmi (ADV) en yüksek olan 40 hisseyi seçer.
    Ardından "Zombi" ve "Gap" filtrelerinden geçirerek temiz bir Active Universe oluşturur.
    """
    def __init__(self, data_fetcher, db_manager: DatabaseManager):
        self.fetcher = data_fetcher
        self.db = db_manager

        # Basitlik için varsayılan BIST100 (veya genişletilmiş 30-50 hisse) listesi.
        # Gerçekte 'all_bist_tickers.txt' gibi bir dosyadan okunabilir.
        self.base_symbols = [
            "AKBNK", "ALARK", "ARCLK", "ASELS", "ASTOR", "BIMAS", "BRSAN", "CWISE",
            "EKGYO", "ENKAI", "EREGL", "FROTO", "GARAN", "GUBRF", "HEKTS", "ISCTR",
            "KCHOL", "KONTR", "KOZAA", "KOZAL", "KRDMD", "ODAS", "OYAKC", "PETKM",
            "PGSUS", "SAHOL", "SASA", "SISE", "TCELL", "THYAO", "TOASO", "TUPRS", "YKBNK",
            "MGROS", "TTKOM", "KORDS", "GARFA", "YKSLN", "VESBE", "ZOREN", "ENJSA", "AEFES"
        ]

    def update_active_universe(self) -> list:
        """
        Haftada bir kez (Örn: Cuma kapanışından sonra) çalışarak yfinance üzerinden
        tüm hisselerin son 20 günlük verisini çeker, ADV'ye göre sıralar ve
        sağlık filtrelerinden (Zombi & Gap) geçirir.

        Returns:
            list: Temizlenmiş, aktif işlem yapılabilecek sembol listesi (Örn: ['THYAO.IS', ...])
        """
        logger.info("Dinamik Hisse Havuzu (Active Universe) güncelleniyor...")

        active_symbols = []
        symbol_data = []

        try:
            for sym in self.base_symbols:
                # yfinance formatına uygun olması için .IS ekle (Eğer ekli değilse)
                full_sym = sym if sym.endswith(".IS") else f"{sym}.IS"

                # Fetch last 20 days
                df = self.fetcher.fetch_ohlcv(full_sym, interval="1d", n_bars=20)

                if df.empty or len(df) < 20:
                    continue

                # 1. Ortalama Günlük İşlem Hacmi (ADV) Hesaplaması
                # ADV = Günlük Kapanış Fiyatı * Günlük Hacim
                # Son 20 günün ortalamasını al
                adv_20d = (df['close'] * df['volume']).mean()

                # Zombi ve Gap filtresi için hesaplamalar
                # ATR Hesapla (pandas_ta ile)
                df.ta.atr(length=14, append=True)

                # Gap sayımı (+%9.9 veya -%9.9)
                # Kapanış ile bir sonraki günün açılışı arasındaki fark
                gaps = abs(df['open'] - df['close'].shift(1)) / df['close'].shift(1) * 100.0
                gap_count = len(gaps[gaps >= 9.9])

                # Son ATR'nin Kapanışa Oranı (Volatilite Yüzdesi)
                last_atr = df['ATRr_14'].iloc[-1] if 'ATRr_14' in df.columns else (df['atr'].iloc[-1] if 'atr' in df.columns else 0.0)
                last_close = df['close'].iloc[-1]
                volatility_pct = (last_atr / last_close) * 100.0 if last_close > 0 else 0.0

                symbol_data.append({
                    'symbol': full_sym,
                    'adv': adv_20d,
                    'volatility_pct': volatility_pct,
                    'gap_count': gap_count
                })

            # 2. Hisseleri ADV değerine göre büyükten küçüğe sırala ve en yüksek hacimli ilk 40'ı seç
            df_symbols = pd.DataFrame(symbol_data)

            if df_symbols.empty:
                logger.error("Hisse havuzu güncellenemedi, veri çekilemedi.")
                return []

            df_top40 = df_symbols.sort_values(by='adv', ascending=False).head(40)

            # 3. Zombi ve Manipülasyon Filtresi (Health Check)
            clean_symbols = []

            for _, row in df_top40.iterrows():
                sym = row['symbol']
                vol_pct = row['volatility_pct']
                gaps = row['gap_count']

                # Zombi Filtresi: Volatilite %1'in altındaysa bu hisse ölüdür.
                if vol_pct < 1.0:
                    logger.debug(f"Zombi Filtresi: {sym} reddedildi (Volatilite: %{vol_pct:.2f})")
                    continue

                # Gap (Boşluk) Filtresi: Son 20 günde 3'ten fazla kez Tavan/Taban boşluğu yapmışsa
                if gaps > 3:
                    logger.debug(f"Gap Filtresi: {sym} reddedildi (Gap Sayısı: {gaps})")
                    continue

                clean_symbols.append(sym)

            # Kalan temiz ve hacimli hisseleri veritabanına kaydet
            self._save_to_db(clean_symbols, df_top40)

            logger.info(f"Active Universe güncellendi. Toplam {len(clean_symbols)} hisse seçildi.")
            return clean_symbols

        except Exception as e:
            logger.error(f"Active Universe güncelleme hatası: {e}")
            return self.get_active_universe() # Fallback to existing

    def _save_to_db(self, symbols: list, df_top40: pd.DataFrame):
        try:
            from datetime import datetime
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM active_universe") # Eski havuzu temizle

                insert_data = []
                for sym in symbols:
                    adv = df_top40[df_top40['symbol'] == sym]['adv'].iloc[0]
                    insert_data.append((sym, float(adv), datetime.now().isoformat()))

                cursor.executemany("INSERT INTO active_universe (symbol, adv_20d, last_updated) VALUES (?, ?, ?)", insert_data)
                conn.commit()
        except Exception as e:
            logger.error(f"Active Universe DB kayıt hatası: {e}")

    def get_active_universe(self) -> list:
        """
        Döngü her saat başı çalışırken hisse listesini bu fonksiyondan çeker.
        (Her seferinde API çağrısı yapmaz, DB'deki güncel temiz listeyi okur).
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT symbol FROM active_universe")
                rows = cursor.fetchall()
                if rows:
                    return [row[0] for row in rows]
                else:
                    # DB boşsa ilk güncellemeyi tetikle
                    return self.update_active_universe()
        except Exception as e:
            logger.error(f"Active Universe okuma hatası: {e}")
            # Fallback
            return [s + ".IS" for s in self.base_symbols[:30]]

    """
    [QUANT MİMARI NOTU - DİNAMİK EVREN SEÇİMİ (DYNAMIC UNIVERSE SELECTION)]
    Neden sabit (Hardcoded) hisse listesi kullanmamalıyız?
    Geçen yılın en hacimli hissesi (Örn: SASA), bu yıl hacmini tamamen kaybedip
    yataya (Zombi Moda) bağlamış olabilir.

    Eğer stratejilerinizi hacimsiz (Sığ) bir hissede koşturursanız, aldığınız "AL"
    sinyalleri tamamen illüzyon (Gürültü/Noise) olacaktır. Zombi filtresi, ölü hisseleri
    havuzdan atar. Gap filtresi ise sürekli Tavan/Taban gidip gelen manipülatif (Pump & Dump)
    hisselerden sermayeyi korur. Kurumsal paranın işlem yaptığı hisse havuzu
    sürekli dinamik olarak "En Likit" (ADV Top 40) olanlardan seçilmelidir.
    """
