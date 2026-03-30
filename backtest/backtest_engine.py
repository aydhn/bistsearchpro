import yfinance as yf
import pandas as pd
from config.config_manager import ConfigManager
from core.indicators import IndicatorEngine
from strategies.core_strategy import CoreStrategy
from core.risk_manager import RiskManager
from core.logger_engine import LoggerEngine
from core.universe import Universe

logger = LoggerEngine.get_system_logger()

# "Geleceği Görme" (Look-ahead bias) hatasına düşmemek için Event-Driven Simulation (Olay Döngüsü).
# Vektörel backtest yerine, barları tek tek ilerleterek sistemi "sanki o an canlıymış gibi" simüle eder.
# Kayma (Slippage) ve Komisyon BIST gerçeklerini yansıtmak için eklenir.

class BacktestEngine:
    def __init__(self, initial_balance=100000, start_date="2021-01-01", end_date="2023-12-31"):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.start_date = start_date
        self.end_date = end_date
        self.open_positions = []
        self.trade_history = []

        self.commission = float(ConfigManager.get("trading_parameters", "COMMISSION_RATE") or 0.001)
        self.slippage = float(ConfigManager.get("trading_parameters", "SLIPPAGE_RATE") or 0.001)

    def load_data(self, symbols):
        logger.info(f"Backtest için veri indiriliyor... {len(symbols)} Hisse")
        self.data_dict = {}
        for sym in symbols:
            try:
                df = yf.download(sym, start=self.start_date, end=self.end_date, progress=False, show_errors=False)
                if df.empty: continue

                df.columns = df.columns.droplevel(1) if isinstance(df.columns, pd.MultiIndex) else df.columns
                df = df.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close','Volume':'volume'})
                df.ffill(inplace=True)
                df.bfill(inplace=True)

                # İndikatörleri hesapla (Look-ahead bias yok, çünkü iterasyonda sadece geçmişi göreceğiz)
                df = IndicatorEngine.enrich_data(df)
                self.data_dict[sym] = df
            except Exception as e:
                logger.error(f"Veri yükleme hatası: {sym} -> {e}")

    def run(self):
        # Tüm tarihleri birleştir (Ortak zaman ekseni)
        all_dates = pd.DatetimeIndex([])
        for df in self.data_dict.values():
            all_dates = all_dates.union(df.index)
        all_dates = all_dates.sort_values()

        logger.info("Event-Driven Simülasyon Başlıyor...")

        for current_date in all_dates:
            # 1. Çıkış Motoru (Exit Engine & Trailing Stop) - Elimizde olanları sat
            for pos in self.open_positions[:]:
                sym = pos['symbol']
                df = self.data_dict[sym]

                if current_date not in df.index: continue

                current_bar = df.loc[current_date]
                high, low, close = current_bar['high'], current_bar['low'], current_bar['close']

                # Stop Loss kontrolü (Slippage ile)
                if low <= pos['current_sl']:
                    exit_price = pos['current_sl'] * (1 - self.slippage)
                    pnl = (exit_price - pos['entry_price']) * pos['lot_size']
                    self.balance += (exit_price * pos['lot_size']) - (exit_price * pos['lot_size'] * self.commission)
                    self.trade_history.append({'symbol': sym, 'pnl': pnl, 'type': 'SL'})
                    self.open_positions.remove(pos)
                    continue

                # Take Profit kontrolü (Slippage ile)
                if high >= pos['take_profit']:
                    exit_price = pos['take_profit'] * (1 - self.slippage)
                    pnl = (exit_price - pos['entry_price']) * pos['lot_size']
                    self.balance += (exit_price * pos['lot_size']) - (exit_price * pos['lot_size'] * self.commission)
                    self.trade_history.append({'symbol': sym, 'pnl': pnl, 'type': 'TP'})
                    self.open_positions.remove(pos)
                    continue

                # Trailing Stop Güncellemesi
                atr_sl_mult = float(ConfigManager.get("strategy_settings", "ATR_MULTIPLIER_SL") or 1.5)
                new_sl = close - (atr_sl_mult * current_bar['ATR'])
                if close >= pos['entry_price'] + (1.5 * current_bar['ATR']) and new_sl < pos['entry_price']:
                     new_sl = pos['entry_price']

                if new_sl > pos['current_sl']:
                    pos['current_sl'] = new_sl

            # 2. Giriş Motoru (Entry Engine) - Yeni Sinyalleri Al
            for sym, df in self.data_dict.items():
                if current_date not in df.index: continue

                # "Geçmişi" taklit etmek için df'i o güne kadar kesiyoruz (Look-ahead bias koruması)
                past_df = df.loc[:current_date]
                if len(past_df) < 50: continue

                signal_data = CoreStrategy.generate_signal(past_df, sym)

                if signal_data['signal'] == 1:
                    # Basit Risk Yöneticisi (PortfolioManager Mock edilerek)
                    if len(self.open_positions) < int(ConfigManager.get("trading_parameters", "MAX_OPEN_POSITIONS") or 8):
                        if not any(p['symbol'] == sym for p in self.open_positions):

                            entry_price = signal_data['close'] * (1 + self.slippage)
                            stop_loss = entry_price - (1.5 * signal_data['atr'])
                            take_profit = entry_price + (3.0 * signal_data['atr'])

                            lot_size = RiskManager.calculate_position_size(self.balance, entry_price, stop_loss)
                            cost = (lot_size * entry_price) * (1 + self.commission)

                            if lot_size > 0 and cost <= self.balance:
                                self.balance -= cost
                                self.open_positions.append({
                                    'symbol': sym,
                                    'entry_price': entry_price,
                                    'current_sl': stop_loss,
                                    'take_profit': take_profit,
                                    'lot_size': lot_size
                                })

        return self._generate_tearsheet()

    def _generate_tearsheet(self):
        # Maksimum Çöküş (Max Drawdown) ve diğer Kurumsal Performans Metrikleri
        df_trades = pd.DataFrame(self.trade_history)
        if df_trades.empty:
            return "İşlem bulunamadı."

        total_trades = len(df_trades)
        wins = df_trades[df_trades['pnl'] > 0]
        losses = df_trades[df_trades['pnl'] <= 0]

        win_rate = (len(wins) / total_trades) * 100
        profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if losses['pnl'].sum() != 0 else float('inf')

        # Basit Drawdown (Zaman serisi olmadığı için sadece PnL serisinden)
        cumulative = df_trades['pnl'].cumsum()
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / (running_max + self.initial_balance)
        max_drawdown = drawdown.min() * 100

        report = (f"🔬 **BACKTEST TAMAMLANDI (Son 3 Yıl)**\n"
                  f"Test Edilen Hisse Sayısı: {len(self.data_dict)}\n"
                  f"Başlangıç Kasası: {self.initial_balance:,.2f} TL | Bitiş: {self.balance:,.2f} TL\n"
                  f"Win-Rate: %{win_rate:.1f}\n"
                  f"Kâr Çarpanı: {profit_factor:.2f}\n"
                  f"Max Drawdown: %{max_drawdown:.1f}\n"
                  f"Detaylı rapor yerel dizine (backtest_results.txt) kaydedildi.")

        with open("backtest_results.txt", "w") as f:
            f.write(report)

        return report
