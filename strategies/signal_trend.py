from dataclasses import dataclass
import logging
from strategies.indicators import IndicatorPipeline
from strategies.regime_filter import RegimeFilter

logger = logging.getLogger(__name__)

@dataclass
class SignalResponse:
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence_score: float
    strategy_name: str

class TrendFollowingEngine:
    """
    Belirgin fiyat hareketlerinde çalışacak ana algoritma.
    Sadece REGIME_TREND ve BULL piyasalarında aktiftir.
    """

    @staticmethod
    def generate_signal(symbol, df_ind, regime_info):
        """
        Kapanış fiyatı EMA(20)'yi yukarı kestiğinde VE
        MACD histogramı sıfırın üzerine çıktığında sinyal üretilir.
        """
        if df_ind is None or df_ind.empty or regime_info is None:
            return None

        # 1. Rejim Kontrolü
        if regime_info.get('regime') != 'REGIME_TREND' or regime_info.get('direction') != 'BULL':
            logger.debug(f"{symbol} TrendFollowing atlandı. Rejim: {regime_info.get('regime')}, Yön: {regime_info.get('direction')}")
            return None

        # 2. Giriş Kuralı
        # Son iki barı alarak kesişimi (crossover) vektörel kontrol edeceğiz.
        if len(df_ind) < 2:
            return None

        latest = df_ind.iloc[-1]
        previous = df_ind.iloc[-2]

        # Kapanış > EMA(20) yukarı kesişimi
        close_curr = latest['close']
        close_prev = previous['close']

        # 'ema_20' is the mapped name from Faz 9 IndicatorPipeline
        ema20_curr = latest.get('ema_20')
        ema20_prev = previous.get('ema_20')

        if not ema20_curr or not ema20_prev:
             return None

        crossover_ema = (close_prev <= ema20_prev) and (close_curr > ema20_curr)

        # MACD Histogramı > 0
        macd_hist = latest.get('macd_hist')
        if macd_hist is None:
             return None

        macd_positive = macd_hist > 0

        # Sinyal Üretimi
        if crossover_ema and macd_positive:
            # 3. Risk Yönetimi Çıktısı (ATR tabanlı)
            atr_val = latest.get('atr_14')
            if not atr_val:
                logger.warning(f"ATR bulunamadığı için {symbol} TrendFollowing sinyali iptal edildi.")
                return None

            entry_price = close_curr
            stop_loss = entry_price - (2 * atr_val)
            take_profit = entry_price + (3 * atr_val)

            # Trend gücüne (ADX) göre confidence score belirleme (25 üstü trenddir, 50 çok güçlüdür)
            adx_val = regime_info.get('adx_value', 25)
            # Normalize ADX between 25 and 50 -> 60% to 100% confidence
            confidence = min(100.0, 60.0 + ((adx_val - 25) / 25) * 40.0)

            signal = SignalResponse(
                symbol=symbol,
                direction="BUY",
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence_score=round(confidence, 2),
                strategy_name="TrendFollowing"
            )

            logger.info(f"TrendFollowing Sinyali Üretildi: {signal}")
            return signal

        return None
