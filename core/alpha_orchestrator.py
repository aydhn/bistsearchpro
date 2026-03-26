import logging
from strategies.strategy_factory import StrategyFactory
from data.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class AlphaOrchestrator:
    """
    3 farklı strateji aynı anda farklı hisselerde sinyal üretebilir. Hangisine güveneceğiz?
    Bunu çözecek olan "Orkestra Şefi" sınıfı.
    Her stratejinin geçmiş performansına (Sanal Kârlılık - Paper PnL) göre
    dinamik olarak güvenilirlik (Ağırlık - Kelly Yüzdesi) tayin eder.
    Sermaye rotasyonunu (Capital Rotation) maksimize eder.
    """
    def __init__(self, db_manager: DatabaseManager, strategy_factory: StrategyFactory):
        self.db = db_manager
        self.factory = strategy_factory

        # Her stratejinin başlangıç güvenilirlik skoru %50 (0.5)
        self.strategy_weights = {
            "Mean_Reversion": 0.5,
            "Trend_Following": 0.5,
            "Volatility_Breakout": 0.5,
            "Statistical_Arbitrage": 0.5
        }

    def update_strategy_weights(self):
        """
        Geçmiş 30 günlük işlem kayıtlarına (trade_journal) bakarak her bir
        alt stratejinin (Mean_Reversion vs) kazanma oranını (Win Rate) veya
        Toplam PnL'sini hesaplar ve ağırlıklarını (Weight) günceller.
        Eğer bir strateji sürekli stop oluyorsa ağırlığı (güvenilirliği) sıfıra yaklaşır.
        """
        logger.info("Alpha Orkestratörü: Strateji güvenilirlik skorları (ağırlıklar) güncelleniyor...")
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Her stratejinin toplam işlem sayısı ve kârlı işlem sayısını çek (Son 30 gün vs)
                # Basitlik için tüm KAPALI işlemlere bakıyoruz. Gerçekte zaman filtresi eklenmelidir.
                cursor.execute("""
                    SELECT strategy_source,
                           COUNT(*) as total_trades,
                           SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                           SUM(pnl) as net_pnl
                    FROM trade_journal
                    WHERE status = 'CLOSED'
                    GROUP BY strategy_source
                """)

                rows = cursor.fetchall()

                if not rows:
                    logger.debug("Yeterli işlem geçmişi yok, varsayılan ağırlıklar (%50) korunuyor.")
                    return

                # Performans ölçümü (Örn: Win Rate üzerinden)
                for row in rows:
                    source = row[0]
                    total = row[1]
                    winning = row[2]

                    if source in self.strategy_weights and total >= 5: # En az 5 işlem yapılmışsa güven
                        win_rate = winning / total
                        # Ağırlığı Win Rate'e veya Net PnL'ye göre ayarla (0.0 ile 1.0 arası)
                        # Sadece Win Rate'e eşitliyoruz (Örn: %60 başarı = 0.6 ağırlık)
                        self.strategy_weights[source] = win_rate
                        logger.info(f"Strateji Güncellendi: {source} -> Yeni Ağırlık: {win_rate:.2f} (Toplam İşlem: {total})")

        except Exception as e:
            logger.error(f"Alpha Orchestrator ağırlık güncelleme hatası: {e}")

    def process_signals(self, df_ind, symbol, current_regime):
        """
        StrategyFactory'den (Fabrikadan) gelen tüm çiğ (raw) sinyalleri alır,
        kendi ağırlık (güvenilirlik) filtresinden geçirerek tek bir NİHAİ "AL" sinyali seçer.
        (Veya birden fazlasına onay verebilir).
        """
        raw_signals = self.factory.generate_signals(df_ind, symbol, current_regime)

        if not raw_signals:
            return None

        approved_signals = []

        for source, signal in raw_signals.items():
            # Stratejinin anlık güvenilirlik skorunu al (Varsayılan 0.5)
            weight = self.strategy_weights.get(source, 0.5)

            # Eğer strateji çok kötü gidiyorsa (Örn Win Rate < %35 ise), ürettiği sinyali tamamen REDDET.
            if weight < 0.35:
                logger.debug(f"Alpha Orkestratörü REDDİ: {source} stratejisinin güvenilirliği çok düşük ({weight:.2f}). Sinyal çöpe atıldı.")
                continue

            # Orijinal sinyalin güven skoruyla orkestratörün ağırlığını çarp (Harmanla)
            # Örn: Fabrika %80 emin, ama stratejinin genel Win Rate'i %60 (0.6).
            # Nihai Güven = 80 * 0.6 = 48.0
            final_confidence = signal.get("confidence", 50.0) * weight

            # Harmanlanmış skor %45'in üzerindeyse onay listesine al
            if final_confidence >= 45.0:
                signal["final_confidence"] = final_confidence
                # Telegram mesajına eklenecek "Kaynak" ve "Skor" metnini hazırla
                signal["report_text"] = f"[⚙️ Kaynak: {source} | Güncel Başarı: %{weight*100:.0f}]"
                approved_signals.append(signal)

        if not approved_signals:
            return None

        # Eğer aynı hisse için birden fazla strateji AL diyorsa (Örn Hem Reversion hem Breakout),
        # en yüksek harmanlanmış skora sahip olanı "Şampiyon" seç.
        approved_signals.sort(key=lambda x: x["final_confidence"], reverse=True)
        best_signal = approved_signals[0]

        logger.info(f"Alpha Orkestratörü ONAYI: {symbol} için Şampiyon Strateji -> {best_signal['source']} (Skor: {best_signal['final_confidence']:.2f})")
        return best_signal

    """
    [QUANT MİMARI NOTU - DİNAMİK ALPHA DAĞITIMI VE ÇOKLU STRATEJİ]
    Kurumsal fonlar piyasayı tek bir gözle (Örn: Sadece Trend takipçisi) izlemez.
    Çoklu Strateji Orkestrasyonu, birden fazla farklı beyni (Mean Reversion, Breakout vb.)
    aynı anda masaya oturtur ve "Bugün kim haklı?" diye sorar.

    Eğer piyasa yatay testeredeyse (Whipsaw), Trend Follower stratejisi sürekli zarar
    yazmaya (Drawdown) başlar. Alpha Orkestratörü bunu fark eder ve onun sesini kısar
    (Ağırlığını sıfırlar). Aynı anda Mean Reversion stratejisi tıkır tıkır kâr ediyordur,
    onun sesini açar (Ağırlığını 1.0'a yaklaştırır).

    Bu sayede portföyünüzün "Sharpe Oranı" (Sharpe Ratio), matematiksel olarak
    sabit bir stratejiye göre çok daha stabil bir şekilde maksimize edilir.
    """
