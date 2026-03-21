import logging
from strategies.signal_trend import SignalResponse

logger = logging.getLogger(__name__)

class MeanReversionEngine:
    """
    Piyasanın yönsüz olduğu durumlarda (Yatay - Range)
    istatistiksel merkeze dönüş prensibini kullanan algoritma.
    """

    @staticmethod
    def generate_signal(symbol, df_ind, regime_info):
        """
        Piyasa rejimi REGIME_RANGE olduğunda çalışır.
        Giriş: Fiyat Bollinger Alt Bandına dokunur veya inerse VE
               RSI(14) 30 seviyesini aşağıdan yukarıya keserse aşırı satım sinyali üretir.
        """
        if df_ind is None or df_ind.empty or regime_info is None:
            return None

        # 1. Rejim Kontrolü
        if regime_info.get('regime') != 'REGIME_RANGE':
            logger.debug(f"{symbol} MeanReversion atlandı. Rejim: {regime_info.get('regime')}")
            return None

        # En az 2 bar veri lazım
        if len(df_ind) < 2:
            return None

        latest = df_ind.iloc[-1]
        previous = df_ind.iloc[-2]

        close_curr = latest['close']
        close_prev = previous['close']

        bb_lower = latest.get('bb_lower')
        if not bb_lower:
            return None

        rsi_curr = latest.get('rsi_14')
        rsi_prev = previous.get('rsi_14')

        if not rsi_curr or not rsi_prev:
             return None

        # 2. Giriş Kuralı
        # Fiyat BB alt bandının altına inerse veya dokunursa ( <= BB_LOWER)
        price_below_bb = close_curr <= bb_lower

        # RSI 30'u yukarı keserse (Aşırı satımdan çıkış)
        rsi_crossover = (rsi_prev <= 30) and (rsi_curr > 30)

        # Sinyal Üretimi
        if price_below_bb and rsi_crossover:
            # 3. Risk Çıktısı
            # Take-Profit: Bollinger Orta Bandı (SMA 20 -> ema_20 veya bb_mid)
            bb_mid = latest.get('bb_mid')
            if not bb_mid:
                logger.warning(f"BB_MID bulunamadığı için {symbol} MeanReversion iptal edildi.")
                return None

            entry_price = close_curr
            take_profit = bb_mid

            # Stop-Loss: Giriş mumunun low değerinin %1 altı
            low_curr = latest['low']
            stop_loss = low_curr * 0.99

            # Yatay piyasada marj dar olduğu için Kar Al mesafesi Stop Loss mesafesinden büyük olmalıdır
            # R/R oranı < 1 ise işlemi alma (opsiyonel ama sağlıklı bir filtre)
            risk = entry_price - stop_loss
            reward = take_profit - entry_price

            if risk > 0 and (reward / risk) < 1.0:
                 logger.debug(f"{symbol} MeanReversion iptal: Risk/Reward oranı çok düşük ({reward/risk:.2f}).")
                 return None

            # Confidence: ADX düşüklüğüne göre ters orantılı (ADX ne kadar düşükse yataylık o kadar iyidir)
            adx_val = regime_info.get('adx_value', 25)
            # Normalize ADX between 10 and 25 -> 100% to 60% confidence
            confidence = max(60.0, 100.0 - ((adx_val - 10) / 15) * 40.0)

            signal = SignalResponse(
                symbol=symbol,
                direction="BUY",
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence_score=round(confidence, 2),
                strategy_name="MeanReversion"
            )

            logger.info(f"MeanReversion Sinyali Üretildi: {signal}")
            return signal

        return None
