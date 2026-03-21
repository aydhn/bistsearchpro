import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class VectorizedBacktester:
    """
    Saf NumPy/Pandas vektörel backtest motoru.
    İşlem simülasyonunu komisyon, slippage ve risksiz getiri (Sharpe) ile gerçekçi yapar.
    """

    @staticmethod
    def run_backtest(df_ind, signal_condition, sl_pct=0.02, tp_pct=0.03):
        """
        Gelen indikatörlü DataFrame'e ve bool tipindeki signal_condition Serisine
        göre vektörel backtest çalıştırır.
        """
        if df_ind is None or df_ind.empty or signal_condition.sum() == 0:
            logger.warning("Backtest için yeterli sinyal veya veri yok.")
            return None

        # Gerçekçilik Parametreleri
        COMMISSION_RATE = 0.0025 # Binde 2.5 (Giriş ve Çıkış için toplam işlem maliyeti tahmini)
        SLIPPAGE_RATE = 0.0015   # Binde 1.5 (%0.15)
        RISK_FREE_RATE = 0.35    # Yıllık %35 risksiz getiri oranı (Türkiye için varsayılan)

        df_ind = df_ind.copy()

        # Sinyalin geldiği günün bir sonraki açılışında (Open) işleme girilir (Look-ahead bias önleme)
        df_ind['signal'] = signal_condition
        df_ind['entry_signal'] = df_ind['signal'].shift(1).fillna(False)

        # Giriş Fiyatlarına Slippage Ekleme (Daha pahalıya alma simülasyonu)
        df_ind['raw_entry'] = np.where(df_ind['entry_signal'], df_ind['open'], np.nan)
        df_ind['entry_price'] = df_ind['raw_entry'] * (1 + SLIPPAGE_RATE)

        # Stop-Loss ve Take-Profit Seviyeleri (Ham giriş üzerinden, ancak slippage ile vurma ihtimali)
        df_ind['stop_loss'] = np.where(df_ind['entry_signal'], df_ind['raw_entry'] * (1 - sl_pct), np.nan)
        df_ind['take_profit'] = np.where(df_ind['entry_signal'], df_ind['raw_entry'] * (1 + tp_pct), np.nan)

        df_ind['active_sl'] = df_ind['stop_loss'].ffill()
        df_ind['active_tp'] = df_ind['take_profit'].ffill()

        hit_sl = df_ind['low'] <= df_ind['active_sl']
        hit_tp = df_ind['high'] >= df_ind['active_tp']

        df_ind['exit_signal'] = hit_sl | hit_tp

        # Çıkış Fiyatlarına Slippage Ekleme (Daha ucuza satma simülasyonu)
        # Eğer SL vurursa, fiyat SL'den daha aşağıda gerçekleşmiş olabilir (olumsuz kayma)
        df_ind['exit_price_sl'] = df_ind['active_sl'] * (1 - SLIPPAGE_RATE)
        # Eğer TP vurursa, TP'de satılır (burada slippage pozitif de olabilir ama biz konservatif olup kaydırmayalım veya negatif kaydıralım)
        df_ind['exit_price_tp'] = df_ind['active_tp'] * (1 - SLIPPAGE_RATE)

        df_ind['exit_price'] = np.where(hit_sl, df_ind['exit_price_sl'],
                               np.where(hit_tp, df_ind['exit_price_tp'], np.nan))

        entries = df_ind[df_ind['entry_signal']].index

        trades = []
        for entry_idx in entries:
            future_exits = df_ind.loc[entry_idx:][df_ind.loc[entry_idx:, 'exit_signal']]
            if not future_exits.empty:
                exit_idx = future_exits.index[0]
                exit_price = future_exits.iloc[0]['exit_price']
                entry_price = df_ind.loc[entry_idx, 'entry_price']

                # Getiri oranı hesaplama ve Komisyon Düşümü
                # Net Getiri = (Çıkış - Giriş) / Giriş - Komisyon (Çift yönlü düşünülürse 2x komisyon, ama biz toplam komisyon rate belirledik)
                gross_ret = (exit_price - entry_price) / entry_price
                net_ret = gross_ret - COMMISSION_RATE

                trades.append({
                    'entry_time': entry_idx,
                    'exit_time': exit_idx,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'return_pct': net_ret,
                    'win': net_ret > 0
                })

        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'cumulative_return_pct': 0.0,
                'max_drawdown_pct': 0.0,
                'sharpe_ratio': 0.0,
                'warning': "Sinyal üretilmedi."
            }

        trades_df = pd.DataFrame(trades)

        total_trades = len(trades_df)
        win_rate = trades_df['win'].mean()

        trades_df['cum_return'] = (1 + trades_df['return_pct']).cumprod()
        cumulative_return = trades_df['cum_return'].iloc[-1] - 1.0

        trades_df['peak'] = trades_df['cum_return'].cummax()
        trades_df['drawdown'] = (trades_df['cum_return'] - trades_df['peak']) / trades_df['peak']
        max_drawdown = trades_df['drawdown'].min()

        # Sharpe Oranı Hesaplama (Yıllıklandırılmış)
        # Günlük getiri verisi olmadığı için trade başına getirilerin standart sapmasını alıyoruz.
        # Bu basitleştirilmiş bir Sharpe oranıdır (İşlem bazlı).
        # Risksiz getiri oranını işlem süresine göre ölçeklendirmek gerekir,
        # ancak basitlik adına yıllık risksiz getiriyi işlem sayısına bölüyoruz (varsayılan 252 işlem günü).

        avg_trade_return = trades_df['return_pct'].mean()
        std_trade_return = trades_df['return_pct'].std()

        sharpe_ratio = 0.0
        warning_msg = None

        if std_trade_return > 0:
            # Günlük risksiz getiri eşdeğeri
            daily_rf = RISK_FREE_RATE / 252.0
            # Sharpe = (Ortalama Getiri - Risksiz Getiri) / Getiri Standart Sapması
            # Yıllıklandırmak için sqrt(252) ile çarpıyoruz
            sharpe_ratio = ((avg_trade_return - daily_rf) / std_trade_return) * np.sqrt(252)

            if sharpe_ratio < 1.0:
                warning_msg = "Strateji Yetersiz (Sharpe < 1.0)"

        results = {
            'total_trades': total_trades,
            'win_rate': round(win_rate * 100, 2),
            'cumulative_return_pct': round(cumulative_return * 100, 2),
            'max_drawdown_pct': round(max_drawdown * 100, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'warning': warning_msg
        }

        logger.info(f"Gerçekçi Backtest Tamamlandı: {results}")
        return results
