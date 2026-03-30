import pandas as pd
import numpy as np
import logging

class RiskModeler:
    """
    Monte Carlo Simülasyonu ve Predictive Risk Modelleme (Phase 21).
    Rastgelelik testleri, Probability of Ruin (Çöküş İhtimali) hesaplaması.
    """
    def __init__(self, db_path="data/portfolio.db"):
        self.db_path = db_path

    def run_monte_carlo(self, iterations=1000, future_trades=100):
        """
        Eldeki PnL geçmişinden yerine koyarak rastgele (Bootstraping) simülasyon yapar.
        Aşırı Uyum (Curve Fitting) tuzağına karşı gerçekliği (Probability of Ruin) gösterir.
        """
        import sqlite3
        import os
        if not os.path.exists(self.db_path):
            return None

        with sqlite3.connect(self.db_path) as conn:
            # PnL % yüzdelerini çek
            df = pd.read_sql_query("SELECT pnl_pct FROM trade_history", conn)

        if len(df) < 30:
            logging.warning("Monte Carlo için en az 30 kapanmış işlem gereklidir.")
            return None

        pnl_pool = df['pnl_pct'].values / 100.0 # Yüzdeleri ondalığa çevir

        # 1000 paralel evren, her birinde 100 işlem. Kasa 1.0 (100%) ile başlar.
        simulations = np.zeros((iterations, future_trades))

        for i in range(iterations):
            # Havuzdan rastgele 100 getiri seç (yerine koyarak - with replacement)
            random_returns = np.random.choice(pnl_pool, size=future_trades, replace=True)
            # Kümülatif kasa büyümesi (Compounding)
            equity_curve = np.cumprod(1 + random_returns)
            simulations[i] = equity_curve

        # --- İSTATİSTİKLER ---
        # Probability of Ruin (%20 Çöküş - Kasanın 0.8'in altına inmesi)
        ruin_events = np.sum(np.min(simulations, axis=1) < 0.8)
        prob_of_ruin = (ruin_events / iterations) * 100.0

        # Expected Max Drawdown
        # Her simülasyonun tepeden en dibe çöküşünü hesapla, ortalamasını al
        peak = np.maximum.accumulate(simulations, axis=1)
        drawdowns = (peak - simulations) / peak
        max_drawdowns = np.max(drawdowns, axis=1)
        expected_mdd = np.mean(max_drawdowns) * 100.0

        return {
            "prob_of_ruin": prob_of_ruin,
            "expected_mdd": expected_mdd,
            "simulations": simulations # Visuals_engine için
        }
