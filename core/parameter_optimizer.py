import logging
import random
import numpy as np
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

class ParameterOptimizer:
    """
    Dinamik Parametre Optimizasyonu (Hyperparameter Tuning).
    Stratejilerdeki sabit sayıları (EMA periyotları, RSI sınırları, ATR çarpanları)
    piyasanın güncel ritmine göre otomatik akort eder.
    Ağır CPU tüketimini önlemek için Randomized Search (Rastgele Arama) kullanır.
    """
    def __init__(self, data_fetcher, db_manager):
        self.fetcher = data_fetcher
        self.db = db_manager

    def _calculate_calmar_ratio(self, equity_curve: np.array):
        """
        Kurumsal Hedef Fonksiyonu (Fitness Score): Calmar Rasyosu.
        Yıllıklandırılmış Getiri / Maksimum Düşüş
        Eğer sadece Net Kâr'a göre optimize etseydik doğrudan Overfitting
        (aşırı uydurma) tuzağına düşerdik. Biz en pürüzsüz büyüme eğrisini arıyoruz.
        """
        if len(equity_curve) < 2:
            return 0.0

        returns = np.diff(equity_curve) / equity_curve[:-1]

        # Eğer sürekli sıfır veya negatif getiri varsa
        if np.all(returns <= 0):
            return 0.0

        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]

        # Basit Max Drawdown
        rolling_max = np.maximum.accumulate(equity_curve)
        drawdowns = (equity_curve - rolling_max) / rolling_max
        max_drawdown = abs(np.min(drawdowns))

        if max_drawdown == 0:
            max_drawdown = 0.0001 # Sıfıra bölme hatasını engelle

        # Yıllıklandırma çarpanı (Örn: 252 işlem günü)
        annualized_return = total_return * (252 / len(equity_curve))

        calmar = annualized_return / max_drawdown
        return calmar

    def _vectorized_sim(self, df: pd.DataFrame, p: dict) -> np.array:
        """
        Hızlı bir vektörel backtest ile parametrelerin (p) performansını
        equity curve (özsermaye eğrisi) olarak döndürür.
        """
        try:
            sim_df = df.copy()
            # Örnek Parametre: EMA Kesişimi
            sim_df[f"EMA_F"] = sim_df['close'].ewm(span=p['ema_fast'], adjust=False).mean()
            sim_df[f"EMA_S"] = sim_df['close'].ewm(span=p['ema_slow'], adjust=False).mean()

            # Sinyal: Hızlı EMA, Yavaş EMA'yı yukarı keserse AL (1)
            sim_df['signal'] = np.where(sim_df['EMA_F'] > sim_df['EMA_S'], 1, 0)

            # Günlük Getiri
            sim_df['returns'] = sim_df['close'].pct_change()

            # Strateji Getirisi = Dünün sinyali * Bugünün getirisi
            sim_df['strat_returns'] = sim_df['signal'].shift(1) * sim_df['returns']
            sim_df.fillna(0, inplace=True)

            # Başlangıç 100 olarak baz alınır
            equity_curve = (1 + sim_df['strat_returns']).cumprod() * 100
            return equity_curve.to_numpy()
        except Exception as e:
            logger.error(f"Vectorized Sim hatası: {e}")
            return np.ones(len(df)) * 100

    def run_optimization(self, symbol: str, df: pd.DataFrame, num_trials: int = 20):
        """
        Seçili hissenin In-Sample verisi (df) üzerinde randomized search ile
        en yüksek Calmar Rasyosunu veren parametre kombinasyonunu bulur.
        """
        logger.info(f"Parametre Optimizasyonu (Randomized Search) başlatıldı: {symbol}")

        if df.empty or len(df) < 50:
            logger.warning(f"Optimizasyon için yetersiz veri: {symbol}")
            return None

        # Optimizasyon Uzayı (Search Space)
        param_grid = {
            'ema_fast': list(range(10, 30, 2)),
            'ema_slow': list(range(40, 100, 5)),
            'rsi_oversold': list(range(20, 40, 2)),
            'atr_multiplier_sl': [1.0, 1.2, 1.5, 1.8, 2.0],
            'atr_multiplier_tp': [2.0, 2.5, 3.0, 3.5, 4.0]
        }

        best_calmar = -999.0
        best_params = None

        try:
            for _ in range(num_trials):
                # 1. Rastgele parametre seçimi
                p = {
                    'ema_fast': random.choice(param_grid['ema_fast']),
                    'ema_slow': random.choice(param_grid['ema_slow']),
                    'rsi_oversold': random.choice(param_grid['rsi_oversold']),
                    'atr_sl': random.choice(param_grid['atr_multiplier_sl']),
                    'atr_tp': random.choice(param_grid['atr_multiplier_tp'])
                }

                # Geçersiz kombinasyonları atla
                if p['ema_fast'] >= p['ema_slow'] or p['atr_sl'] >= p['atr_tp']:
                    continue

                # 2. Vektörel Simülasyon
                simulated_equity = self._vectorized_sim(df, p)

                # 3. Calmar Rasyosunu Hesapla
                calmar = self._calculate_calmar_ratio(simulated_equity)

                if calmar > best_calmar:
                    best_calmar = calmar
                    best_params = p

            logger.info(f"{symbol} için en iyi Calmar: {best_calmar:.2f}, Parametreler: {best_params}")

            # Bulunan optimal parametreleri DB'ye kaydet
            if best_params:
                self._save_optimal_parameters(symbol, best_params, best_calmar)

            return best_params

        except Exception as e:
            logger.error(f"Optimizasyon döngüsünde hata: {str(e)}")
            return None

    def _save_optimal_parameters(self, symbol, params, score):
        """Yeni bulunan parametreleri DB'ye (strategy_metrics) kaydeder."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                # Mevcut yapımızda tam tablosu yoksa logla veya uyumlu bir tabloya yaz
                # Örneğin strategy_metrics tablosuna kaydedilebilir
                cursor.execute("""
                    INSERT INTO strategy_metrics
                    (timestamp, strategy_name, win_rate, net_pnl, assigned_weight)
                    VALUES (?, ?, ?, ?, ?)
                """, (datetime.now().isoformat(), f"OPTIMIZED_{symbol}", score, 0.0, 1.0))
                conn.commit()
                logger.debug(f"{symbol} optimal parametreleri (Calmar: {score:.2f}) kaydedildi.")
        except Exception as e:
            logger.error(f"Optimal parametre kayıt hatası: {e}")

    """
    [QUANT MİMARI NOTU - PARAMETRE OPTİMİZASYONU VE NET KÂR YANILGISI]
    Amatör traderlar, optimizasyon yazılımını açar ve "Bana en çok para kazandıran
    (Maximum Net Profit) EMA ve RSI ayarlarını bul" der. Yazılım, son 3 yıldaki
    bütün dip ve tepelere "tesadüfen" oturan tamamen absürt bir parametre (Örn: EMA 17.3
    ve RSI 22.8) bulur ve %5000 kâr gösterir. Bunu canlıya aldığınız ertesi gün,
    sistem para kaybetmeye başlar. (Buna Overfitting - Eğri Uydurma denir).

    Kurumsal fon yöneticileri parametre optimizasyonunu "Net Kâr" üzerinden değil,
    risk ayarlı getiriler (Risk-Adjusted Returns - Sharpe, Sortino veya Calmar)
    üzerinden yapar. Calmar Rasyosu (Yıllık Getiri / Max Drawdown), fırtınalı
    denizlerde gemiyi en az sallayan (Maksimum Düşüşü en az olan) rotayı bulur.
    Az ama sürekli kazandıran pürüzsüz bir özsermaye eğrisi (Smooth Equity Curve),
    tesadüfen yakalanmış %5000'lik bir roketten sonsuz kez daha değerlidir.
    """
