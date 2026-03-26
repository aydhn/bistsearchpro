import logging

logger = logging.getLogger(__name__)

class StrategyFactory:
    """
    Çoklu Strateji Orkestrasyonu (Multi-Strategy Orchestration) için tasarlanmış,
    Farklı piyasa koşullarında çalışan bağımsız algoritmaları paralel yarıştıran fabrika sınıfı.
    "Tek Strateji / Tek Hata Noktası" (Single Point of Failure) riskini yok eder.
    """
    def __init__(self):
        self.strategies = {
            "Mean_Reversion": self._strategy_mean_reversion,
            "Trend_Following": self._strategy_trend_following,
            "Volatility_Breakout": self._strategy_volatility_breakout
        }

    def generate_signals(self, df_ind, symbol, current_regime=None):
        """
        Gelen teknik veriler üzerinden aktif tüm stratejileri koşturur ve
        varsa onaylanmış sinyalleri bir sözlük halinde döndürür.
        """
        if df_ind is None or df_ind.empty:
            return {}

        signals = {}
        for name, strategy_func in self.strategies.items():
            try:
                signal = strategy_func(df_ind, current_regime)
                if signal:
                    signals[name] = signal
            except Exception as e:
                logger.error(f"Strateji hatası ({name} - {symbol}): {e}")

        return signals

    def _strategy_mean_reversion(self, df, current_regime):
        """
        Strateji 1 (Ortalamaya Dönüş): Yatay piyasalar için.
        Bollinger Alt Bandı + RSI Aşırı Satım uyumsuzluklarını arar.
        """
        # Sadece son bar kontrolü (Gerçekte shift(1) ile bir önceki bar onayı gerekir)
        last_bar = df.iloc[-1]

        # Eğer piyasa Boğa (Trend) rejimindeyse, Mean Reversion (Ortalamaya Dönüş)
        # çalışmayabilir. Veya tersine sadece yatay (Range) rejimde çalışması istenir.
        # Bu katı kuralı Alpha Orkestratörü (Ağırlıklandırma) çözecek.

        try:
            close = last_bar['close']
            bb_lower = last_bar['bb_lower']
            rsi = last_bar['rsi']

            # Kural: Fiyat Bollinger Alt Bandına değmiş veya altındaysa (Aşırı satım)
            # VE RSI < 30 (Aşırı satım) ise AL.
            if close <= bb_lower and rsi < 30:
                return {"direction": "BUY", "confidence": 75.0, "source": "Mean_Reversion"}

        except KeyError:
             pass # Gerekli sütun yoksa sessiz geç

        return None

    def _strategy_trend_following(self, df, current_regime):
        """
        Strateji 2 (Momentum / Trend Following): Trend piyasaları için.
        MACD sıfır hattı kesişimi + ADX (Trend Gücü) > 25 onayını arar.
        """
        last_bar = df.iloc[-1]
        try:
            macd = last_bar['macd']
            macd_signal = last_bar['macd_signal']
            adx = last_bar['adx']

            # Kural: MACD, Signal hattını yukarı kesmişse (ve sıfırın altındaysa/yakınındaysa)
            # VE ADX > 25 (Güçlü Trend varsa) ise AL.
            # Vektörel bir "crossover" (kesişim) kontrolü için bir önceki barlara bakılmalı.
            prev_bar = df.iloc[-2]
            prev_macd = prev_bar['macd']
            prev_macd_signal = prev_bar['macd_signal']

            macd_cross_up = (prev_macd < prev_macd_signal) and (macd > macd_signal)

            if macd_cross_up and adx > 25:
                return {"direction": "BUY", "confidence": 80.0, "source": "Trend_Following"}

        except KeyError:
             pass

        return None

    def _strategy_volatility_breakout(self, df, current_regime):
        """
        Strateji 3 (Volatilite Kırılımı): Daralan üçgenler veya yatay kanallar için.
        Fiyatın çok sıkıştığı bölgelerden hacimli fırlamaları (Donchian Kırılımı) yakalar.
        """
        last_bar = df.iloc[-1]
        try:
            close = last_bar['close']
            donchian_upper = last_bar['donchian_upper']
            volume = last_bar['volume']

            # Ortalama hacim (Son 20 gün)
            avg_vol = df['volume'].rolling(20).mean().iloc[-1]

            # Kural: Kapanış 20 günlük Donchian Üst Bandını kırıyorsa (Yeni En Yüksek)
            # VE Hacim, 20 günlük ortalama hacmin en az %150'si (1.5 katı) ise AL.
            if close >= donchian_upper and volume > (avg_vol * 1.5):
                return {"direction": "BUY", "confidence": 85.0, "source": "Volatility_Breakout"}

        except KeyError:
             pass

        return None

    """
    [QUANT MİMARI NOTU - STRATEJİ DİVERSİFİKASYONU]
    Piyasalar sabit bir makineden ibaret değildir; sürekli rejim (durum) değiştirirler.
    "Yazın sat, kışın al" veya "Hareketli ortalama kesişimi" gibi tekil kurallar,
    piyasa yataya sardığında (Range Market) ardı ardına 10 kez stop olur ve
    kasanızı paramparça eder.

    Çözüm: Birbirinden bağımsız çalışan, farklı felsefelere (Ortalamaya Dönüş, Trend Takibi,
    Volatilite Kırılımı) sahip stratejileri aynı anda yarıştırmaktır. Biri batarken diğeri
    çıkar ve sermaye eğrisi (Equity Curve) çok daha pürüzsüz (Smooth) hale gelir.
    """
