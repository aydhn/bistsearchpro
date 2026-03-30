import pandas as pd
import logging
from core.indicators import IndicatorEngine
from core.strategy import StrategyEngine
from core.risk_manager import RiskManager

class BacktestEngine:
    """
    Phase 11: Olay Güdümlü (Event-Driven) Tarihsel Simülatör.
    Look-ahead bias engellenmiş, barları tek tek işleyen kurumsal test motoru.
    """
    def __init__(self, config):
        self.config = config
        self.initial_balance = config['trading_parameters']['INITIAL_BALANCE']
        self.commission = config['trading_parameters']['COMMISSION_RATE_PCT'] / 100.0
        self.slippage = config['trading_parameters']['SLIPPAGE_RATE_PCT'] / 100.0

    def run_backtest(self, symbol: str, df: pd.DataFrame) -> dict:
        """
        Gelen zenginleştirilmiş DataFrame'i (OHLCV + İndikatörler) alıp satır satır işler.
        Dönüş: Performans metrikleri (PnL, Win-Rate, Max Drawdown)
        """
        if df is None or df.empty:
            return {}

        balance = self.initial_balance
        peak_balance = balance
        max_drawdown = 0.0

        position = None # None veya {'entry_price': x, 'lot_size': y, 'sl': z, 'tp': w}
        trades = []

        # Olay Döngüsü (Event Loop)
        for i in range(1, len(df)):
            current_bar = df.iloc[i]
            prev_bar = df.iloc[i-1]

            # --- PORTFÖY YÖNETİMİ (ÇIKIŞ) ---
            if position is not None:
                # Gerçekçi BIST açılışı: Gap (boşluk) açılışı slippage tetikler.
                # Stop Loss Kontrolü: Düşük fiyat SL'yi vurduysa
                if current_bar['low'] <= position['sl']:
                    # Slippage ile kayıp biraz daha artar
                    exit_price = current_bar['open'] if current_bar['open'] < position['sl'] else position['sl']
                    exit_price *= (1.0 - self.slippage) # Kayma cezası

                    net_profit = (exit_price - position['entry_price']) * position['lot_size']
                    net_profit -= (exit_price * position['lot_size'] * self.commission) # Komisyon satışı

                    balance += net_profit + (position['entry_price'] * position['lot_size'])
                    trades.append({'type': 'SL', 'pnl': net_profit})
                    position = None
                    continue

                # Take Profit Kontrolü: Yüksek fiyat TP'yi vurduysa
                if current_bar['high'] >= position['tp']:
                    exit_price = current_bar['open'] if current_bar['open'] > position['tp'] else position['tp']
                    exit_price *= (1.0 - self.slippage)

                    net_profit = (exit_price - position['entry_price']) * position['lot_size']
                    net_profit -= (exit_price * position['lot_size'] * self.commission)

                    balance += net_profit + (position['entry_price'] * position['lot_size'])
                    trades.append({'type': 'TP', 'pnl': net_profit})
                    position = None
                    continue

                # İzleyen Stop (Trailing Stop) Güncellemesi
                # Kapanış bazında ATR ile SL yukarı çekilir
                current_atr = current_bar['atr']
                new_sl = current_bar['close'] - (current_atr * self.config['strategy_settings']['ATR_MULTIPLIER_SL'])
                if new_sl > position['sl']:
                    position['sl'] = new_sl

            # --- SİNYAL ÜRETİMİ (GİRİŞ) ---
            if position is None and prev_bar['signal'] == 1:
                # Sinyal bir önceki bardan geldi, bu barın açılışıyla (slippage) işleme gir.
                entry_price = current_bar['open'] * (1.0 + self.slippage)

                # Basit risk hesabı (RiskManager tam olarak entegre edilebilirdi, backtest için simüle ediliyor)
                risk_amount = balance * (self.config['trading_parameters']['MAX_RISK_PER_TRADE_PCT'] / 100.0)
                sl_distance = current_bar['atr'] * self.config['strategy_settings']['ATR_MULTIPLIER_SL']
                if sl_distance <= 0: continue

                lot_size = int(risk_amount / sl_distance)
                if lot_size <= 0: continue

                total_cost = entry_price * lot_size
                if total_cost > balance: continue

                # Komisyon kesintisi
                balance -= total_cost
                balance -= (total_cost * self.commission)

                sl_price = entry_price - sl_distance
                tp_price = entry_price + (current_bar['atr'] * self.config['strategy_settings']['ATR_MULTIPLIER_TP'])

                position = {'entry_price': entry_price, 'lot_size': lot_size, 'sl': sl_price, 'tp': tp_price}

            # Drawdown Takibi
            if balance > peak_balance:
                peak_balance = balance
            drawdown = (peak_balance - balance) / peak_balance * 100.0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Açık kalan son pozisyonu mark-to-market kapat
        if position is not None:
             exit_price = df.iloc[-1]['close']
             net_profit = (exit_price - position['entry_price']) * position['lot_size']
             balance += net_profit + (position['entry_price'] * position['lot_size'])
             trades.append({'type': 'END', 'pnl': net_profit})

        # --- KURUMSAL PERFORMANS METRİKLERİ ---
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]

        total_trades = len(trades)
        win_rate = (len(winning_trades) / total_trades * 100.0) if total_trades > 0 else 0.0

        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.9 if gross_profit > 0 else 0.0)

        net_pnl = balance - self.initial_balance

        return {
            'symbol': symbol,
            'initial_balance': self.initial_balance,
            'final_balance': balance,
            'net_pnl': net_pnl,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown
        }
