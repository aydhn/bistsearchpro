import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class BacktestEngine:
    """
    Geçmiş verilere dayalı "Vectorized Backtest" motoru.
    Gereksiz döngülerden kaçınarak pandas'ın gücünü kullanır.
    Komisyon oranını (0.04% BİST) dahil eder. Ortalama bir bilgisayarda saniyeler içinde binlerce işlem yapabilir.
    """
    def __init__(self, initial_capital=100000.0, commission_rate=0.0004):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate

    def simulate(self, symbol: str, df: pd.DataFrame, signals_series: pd.Series):
        """
        Signals series, df ile aynı uzunlukta, "AL" (1), "SAT" (-1), ve "YATAY" (0) sinyalleri içerir.
        """
        if df.empty or signals_series.empty:
            logger.warning("Backtest için yeterli veri yok.")
            return {}

        try:
            # İşlem sinyallerini veri tablosuna taşı
            df_backtest = df.copy()
            df_backtest['signal'] = signals_series

            # Basit bir "sürekli piyasada olma" (Always in the market) pozisyon yaklaşımı
            # Veya sadece sinyal geldiğinde AL/SAT (örneğin sadece long pozisyonları takip eden bir yaklaşım)
            # Long pozisyon için, bir önceki sinyal '1' ise pozisyon '1'dir (aktif).
            df_backtest['position'] = df_backtest['signal'].replace(to_replace=0, method='ffill')

            # Sadece Long işlemler yapıldığını varsayarsak, negatif pozisyonları 0 yap
            df_backtest['position'] = df_backtest['position'].apply(lambda x: 1 if x == 1 else 0)

            # Günlük Logaritmik veya Yüzdesel Getiri
            df_backtest['daily_return'] = df_backtest['close'].pct_change()

            # Strateji Getirisi = Günlük Getiri * Dünün Pozisyonu (pozisyon gece tutulduysa)
            df_backtest['strategy_return'] = df_backtest['daily_return'] * df_backtest['position'].shift(1)

            # Komisyon maliyeti hesaplama (sadece pozisyon değiştiğinde)
            # Eğer dünün pozisyonu ile bugünün pozisyonu farklıysa işlem olmuştur.
            df_backtest['trade'] = df_backtest['position'].diff().abs()
            df_backtest['strategy_return'] = df_backtest['strategy_return'] - (df_backtest['trade'] * self.commission_rate)

            # Nan'ları doldur
            df_backtest.fillna(0, inplace=True)

            # Kümülatif Getiri
            df_backtest['cumulative_strategy'] = (1 + df_backtest['strategy_return']).cumprod()
            df_backtest['cumulative_market'] = (1 + df_backtest['daily_return']).cumprod()

            # Metrik Hesaplamaları
            final_capital = self.initial_capital * df_backtest['cumulative_strategy'].iloc[-1]
            total_trades = int(df_backtest['trade'].sum())

            # Kazanan işlemler yüzdesi
            # Her bir pozisyon kapatıldığındaki net kâr/zarara bakmak vektörel olarak biraz dolaylıdır.
            # Şimdilik sadece pozitif günlük getirileri kazanç olarak varsayıyoruz.
            winning_days = len(df_backtest[(df_backtest['strategy_return'] > 0) & (df_backtest['position'].shift(1) > 0)])
            losing_days = len(df_backtest[(df_backtest['strategy_return'] < 0) & (df_backtest['position'].shift(1) > 0)])

            win_rate = 0.0
            total_active_days = winning_days + losing_days
            if total_active_days > 0:
                win_rate = (winning_days / total_active_days) * 100

            # Profit Factor
            gross_profit = df_backtest[df_backtest['strategy_return'] > 0]['strategy_return'].sum()
            gross_loss = abs(df_backtest[df_backtest['strategy_return'] < 0]['strategy_return'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

            # Maximum Drawdown (Maksimum Düşüş)
            rolling_max = df_backtest['cumulative_strategy'].cummax()
            drawdown = (df_backtest['cumulative_strategy'] - rolling_max) / rolling_max
            max_drawdown = drawdown.min() * 100  # Yüzde olarak

            logger.info(f"Backtest Tamamlandı: {symbol}")
            logger.info(f"Başlangıç: {self.initial_capital:.2f} TL, Bitiş: {final_capital:.2f} TL")
            logger.info(f"İşlem Sayısı: {total_trades}, Win Rate: %{win_rate:.2f}, Profit Factor: {profit_factor:.2f}")

            return {
                "symbol": symbol,
                "initial_capital": self.initial_capital,
                "final_capital": final_capital,
                "total_trades": total_trades,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "max_drawdown_pct": max_drawdown
            }

        except Exception as e:
            logger.error(f"Backtest hesaplaması sırasında hata oluştu: {str(e)}")
            return {}

    # OOS ve Overfitting Dokümantasyonu (Phase 4, Adım 3 uyarınca)
    """
    [QUANT MİMARI NOTU - İSTATİSTİKSEL SAĞLAMLIK VE OVERFITTING]
    Bir stratejinin parametrelerini (örneğin EMA(20) veya RSI(30)) tamamen geçmiş
    verilere uydurarak (Curve Fitting / Overfitting) test etmek, gerçek piyasa
    koşullarında hezimete yol açar. Bill Benter'ın istatistiksel sağlamlık
    felsefesi gereği, geliştirilen sistemlerin geçmiş veri seti ikiye bölünmelidir:

    1. In-Sample (Eğitim Verisi): Stratejinin test edilip parametrelerin bulunduğu periyot.
    2. Out-of-Sample (OOS / Test Verisi): Sistem modelinin "ilk kez karşılaştığı",
       daha önce optimize edilmemiş saf test periyodu.

    OOS (Out-of-Sample) testinde başarı gösteremeyen stratejiler piyasada çökmeye mahkumdur.
    Bu yüzden gerçek sistemler her zaman Walk-Forward Analysis (Geleceğe Dönük Optimizasyon)
    ve OOS onayları ile kullanılmalıdır.
    """
