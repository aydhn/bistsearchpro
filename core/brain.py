import logging
from strategies.regime_filter import RegimeFilter
from strategies.macro_filter import MacroFilter
from strategies.sentiment import TurkishSentimentAnalyzer
from strategies.signal_trend import TrendFollowingEngine
from strategies.signal_reversion import MeanReversionEngine
from strategies.stat_arb import StatArbEngine

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Farklı stratejilerin tartıştığı yönetim kurulu.
    Makro Filtre veya NLP skoru çok negatifse tüm sinyalleri VETO eder.
    Aksi halde sinyalleri toplayıp ağırlıklı puanlama yapar.
    Sadece Confidence Score > %70 olanları işleme onaylar.
    """

    def __init__(self):
        self.sentiment_analyzer = TurkishSentimentAnalyzer()
        self.trend_engine = TrendFollowingEngine()
        self.reversion_engine = MeanReversionEngine()
        self.stat_arb_engine = StatArbEngine()

    def evaluate_signals(self, symbol, df_ind, news_headline=None):
        """
        Gelen DataFrame ve haber başlığı ile çoklu-ajan oylamasını başlatır.
        """
        if df_ind is None or df_ind.empty:
            logger.warning(f"{symbol} için boş veri geldi, orkestratör analiz yapamıyor.")
            return None

        # 1. Makro Filtre (VETO KONTROLÜ 1)
        macro_veto = MacroFilter.get_macro_risk_flag(df_ind, symbol)
        if macro_veto:
            logger.critical(f"Orkestratör: {symbol} için tüm sinyaller MAKRO RİSK nedeniyle VETO edildi.")
            return None

        # 2. Duyarlılık Analizi (VETO KONTROLÜ 2)
        sentiment_score = 0.0
        if news_headline:
            sentiment_score = self.sentiment_analyzer.analyze(news_headline)
            if sentiment_score < -0.5:
                logger.warning(f"Orkestratör: {symbol} için tüm alım sinyaller AŞIRI NEGATİF HABER (Skor: {sentiment_score}) nedeniyle VETO edildi.")
                return None

        # 3. Piyasa Rejimi Tespiti
        regime_info = RegimeFilter.determine_regime(df_ind)
        if not regime_info:
            return None

        # 4. Sinyal Motorlarından Sinyal Toplama
        signals = []

        # Trend Motoru
        trend_sig = self.trend_engine.generate_signal(symbol, df_ind, regime_info)
        if trend_sig:
            signals.append(trend_sig)

        # Ortalama Dönüş Motoru
        reversion_sig = self.reversion_engine.generate_signal(symbol, df_ind, regime_info)
        if reversion_sig:
            signals.append(reversion_sig)

        # StatArb (Örnek kullanım için başka bir sembole ihtiyaç var, burada statik tutuyoruz.
        # Gerçek uygulamada iki hisse yollanmalı.
        # Bu metod sadece tek sembol aldığı için StatArb'ı atlıyoruz veya dışarıdan besliyoruz.)

        if not signals:
            logger.debug(f"Orkestratör: {symbol} için herhangi bir motor sinyal üretmedi.")
            return None

        # 5. Ağırlıklı Puanlama (Weighted Scoring) ve Onaylama
        approved_signals = []
        for sig in signals:
            final_confidence = sig.confidence_score

            # Eğer pozitif haber varsa güven skorunu %10 artır (max 100)
            if sentiment_score > 0.3:
                final_confidence = min(100.0, final_confidence * 1.1)
                logger.debug(f"Pozitif haber desteğiyle güven skoru arttı: {final_confidence:.2f}")

            if final_confidence > 70.0:
                sig.confidence_score = round(final_confidence, 2)
                approved_signals.append(sig)
                logger.info(f"Orkestratör ONAYI: {sig.strategy_name} -> {symbol} Güven: %{sig.confidence_score}")
            else:
                logger.info(f"Orkestratör REDDİ: {sig.strategy_name} -> {symbol} Güven yetersiz: %{final_confidence:.2f}")

        # Eğer birden fazla onaylı sinyal varsa en yüksek güven skorluyu dön
        if approved_signals:
            approved_signals.sort(key=lambda x: x.confidence_score, reverse=True)
            return approved_signals[0]

        return None
