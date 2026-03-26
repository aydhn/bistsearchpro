import logging
import pandas as pd

logger = logging.getLogger(__name__)

class AdvancedBacktester:
    """
    Gelişmiş Olay Yönlendirmeli (Event-Driven) Backtest Motoru.
    Eski basit vektörel backtest'ten (backtest/engine.py) çok daha gerçekçidir.
    DataFrame üzerinde satır satır (tick-by-tick proxy) ilerleyerek, gün içindeki (Intra-bar)
    dinamiklere (önce High mı görüldü yoksa Low mu?) göre Trailing Stop, Kademeli Çıkış
    ve Zaman Stop'unu simüle eder.
    """
    def __init__(self, risk_manager, commission_rate=0.0004):
        self.rm = risk_manager
        self.commission_rate = commission_rate

    def run_simulation(self, symbol: str, df: pd.DataFrame, signals_series: pd.Series):
        """
        Signals series: "AL" (1) sinyallerini barındırır.
        Sonuçları backtest_results.csv'ye yazılacak formata getirir.
        """
        logger.info("Olay Yönlendirmeli (Event-Driven) Backtest başlatıldı...")
        trades = []
        open_position = None

        if df.empty or signals_series.empty:
            return trades

        # Hızlı lookup için DataFrame ve sinyalleri birleştir
        df_sim = df.copy()
        df_sim['signal'] = signals_series

        # Itertuples için index'in datetime string olduğundan emin ol
        if pd.api.types.is_datetime64_any_dtype(df_sim.index):
            df_sim['timestamp_str'] = df_sim.index.astype(str)
        else:
            df_sim['timestamp_str'] = df_sim.index

        try:
            for row in df_sim.itertuples(index=False):
                timestamp = getattr(row, 'timestamp_str', '')
                high = getattr(row, 'high', 0.0)
                low = getattr(row, 'low', 0.0)
                close = getattr(row, 'close', 0.0)
                atr = getattr(row, 'atr', 0.0) if hasattr(row, 'atr') else (getattr(row, 'ATRr_14', 0.0))
                signal = getattr(row, 'signal', 0)

                # Eğer pozisyon açıksa, dinamik çıkışları (Trailing, TP, SL, Time-Stop) kontrol et
                if open_position is not None:
                    # Intra-bar simülasyonu: Mum içinde Stop mu TP mi önce geldi?
                    # Gerçek tick datası olmadığı için varsayımlar (Heuristics) kullanıyoruz.
                    close_price, reason, pnl, new_sl = self._simulate_intrabar(
                        symbol, high, low, close, atr, timestamp, open_position
                    )

                    if new_sl is not None and new_sl != open_position['sl']:
                        open_position['sl'] = new_sl

                    if close_price is not None:
                        # Pozisyon kapandı
                        open_position['exit_price'] = close_price
                        open_position['exit_time'] = timestamp
                        open_position['pnl_pct'] = pnl
                        open_position['exit_reason'] = reason
                        trades.append(open_position)
                        open_position = None

                # Eğer pozisyon kapalıysa ve AL sinyali varsa pozisyona gir
                if open_position is None and signal == 1:
                    # Giriş fiyatına kayma (slippage) ve komisyon yansıt (Execution Simulator mantığı)
                    # Basit simülasyon: Giriş = Kapanış fiyatı
                    entry_price = close

                    is_valid, sl, tp = self.rm.calculate_trade_parameters(entry_price, atr, direction="LONG")

                    if is_valid:
                        open_position = {
                            'symbol': symbol,
                            'direction': 'LONG',
                            'entry_time': timestamp,
                            'entry_price': entry_price,
                            'sl': sl,
                            'tp': tp,
                            'atr_at_entry': atr,
                            'lot_size': 1.0 # Basitlik için
                        }

            # Döngü bittiğinde açık kalan pozisyon varsa anlık fiyattan kapat
            if open_position is not None:
                last_close = df_sim['close'].iloc[-1]
                pnl = ((last_close - open_position['entry_price']) / open_position['entry_price']) - self.commission_rate
                open_position['exit_price'] = last_close
                open_position['exit_time'] = df_sim['timestamp_str'].iloc[-1]
                open_position['pnl_pct'] = pnl
                open_position['exit_reason'] = 'END_OF_BACKTEST'
                trades.append(open_position)

        except Exception as e:
            logger.error(f"Backtest iterasyonunda hata: {e}")

        return trades

    def _simulate_intrabar(self, symbol, high, low, close, atr, timestamp, pos):
        """
        Bir mum içindeki "önce TP mi SL mi vurdu" (Intra-bar) sorunsalını çözer.
        Ayrıca Time-Stop ve Trailing Stop güncellemelerini de kontrol eder.

        Returns:
            (close_price, reason, pnl_pct, new_sl)
        """
        entry_price = pos['entry_price']
        current_sl = pos['sl']
        current_tp = pos['tp']
        entry_time = pos['entry_time']

        # 1. En kötü senaryo: Önce Stop Loss vurdu
        # Barın en düşük noktası SL'nin altındaysa
        if pos['direction'] == 'LONG':
            if low <= current_sl:
                # Stop patladı. Maliyet = Stop fiyatı - komisyon
                pnl = ((current_sl - entry_price) / entry_price) - self.commission_rate
                return current_sl, "STOP_LOSS", pnl, current_sl

            # 2. Barın en yüksek noktası TP'nin üstündeyse
            if high >= current_tp:
                # TP vurdu. Maliyet = TP fiyatı - komisyon
                pnl = ((current_tp - entry_price) / entry_price) - self.commission_rate
                return current_tp, "TAKE_PROFIT", pnl, current_sl

        # Eğer SL veya TP vurmadıysa, barın kapanış fiyatı (veya high) ile Trailing/Time-Stop kontrolü
        res = self.rm.evaluate_dynamic_exit(
            symbol, close, entry_price, current_sl, current_tp, entry_time, atr, pos['lot_size'], pos['direction']
        )

        if res['action'] == 'FULL_CLOSE_TIMEOUT':
            pnl = ((close - entry_price) / entry_price) - self.commission_rate
            return close, "TIME_STOP", pnl, current_sl

        # Kısmi kâr alım simülasyonu backtest'te karmaşıktır (lot düşürmek gerekir).
        # Şimdilik sadece PnL loglama ve yeni SL belirleme odaklıyız.
        # Eğer Trailing stop güncellenmişse, onu döndür ki pozisyon objesine yansısın.
        new_sl = res.get('new_sl', current_sl)

        return None, "", 0.0, new_sl
