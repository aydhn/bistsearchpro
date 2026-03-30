import pandas as pd
import numpy as np
import sqlite3
import os
import matplotlib
import mplfinance as mpf
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from core.logger_engine import LoggerEngine

# "Gelecekteki Olası Çöküşleri" (Drawdown) ve sistemin gerçek "Edge"ini (Matematiksel Avantaj)
# görmek için bir Monte Carlo Simülasyon motoru.

logger = LoggerEngine.get_trade_logger()
os.makedirs("temp_charts", exist_ok=True)

class RiskModeling:
    def __init__(self, db_path="data/portfolio.db"):
        self.db_path = db_path

    def run_monte_carlo(self, iterations=1000, future_trades=100):
        try:
            conn = sqlite3.connect(self.db_path)
            query = "SELECT pnl_percent FROM trade_history"
            df = pd.read_sql_query(query, conn)
            conn.close()

            if len(df) < 30:
                return "Yeterli veri yok (En az 30 kapanmış işlem gereklidir)."

            pnl_history = df['pnl_percent'].values / 100.0  # Yüzdelik getiri

            # Yerine koyarak rastgele seçim (random sampling with replacement)
            simulations = np.zeros((iterations, future_trades + 1))
            simulations[:, 0] = 1.0  # Başlangıç sermayesi (Normalize 1.0)

            for i in range(iterations):
                random_returns = np.random.choice(pnl_history, size=future_trades, replace=True)
                simulations[i, 1:] = np.cumprod(1 + random_returns)

            # Hesaplanacak Kritik Metrikler
            # Probability of Ruin (İflas/Çöküş İhtimali): %20 altına düşüş
            ruin_threshold = 0.8
            ruined_sims = np.sum(np.any(simulations < ruin_threshold, axis=1))
            probability_of_ruin = (ruined_sims / iterations) * 100

            # Beklenen Maksimum Drawdown
            drawdowns = np.zeros(iterations)
            for i in range(iterations):
                running_max = np.maximum.accumulate(simulations[i, :])
                dd = (simulations[i, :] - running_max) / running_max
                drawdowns[i] = dd.min() * 100

            expected_max_drawdown = drawdowns.mean()

            # Görselleştirme (Spaghetti Chart)
            fig, ax = plt.subplots(figsize=(10, 6))
            for i in range(iterations):
                ax.plot(simulations[i, :], color='grey', alpha=0.05)

            # Ortalama (Expected) getiri eğrisi
            mean_sim = simulations.mean(axis=0)
            ax.plot(mean_sim, color='blue', linewidth=2, label="Ortalama Beklenti")

            ax.set_title(f"Monte Carlo Risk Simülasyonu ({iterations} İterasyon)")
            ax.set_xlabel("Gelecekteki İşlem Sayısı")
            ax.set_ylabel("Kümülatif Getiri (Normalize)")
            ax.legend()

            filename = f"temp_charts/monte_carlo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            fig.savefig(filename, dpi=100, bbox_inches='tight')
            plt.close(fig)

            status = "İstikrarlı 🟢" if probability_of_ruin < 10 else "Riskli 🔴"

            report = (f"🎲 **ED CAPITAL KURUMSAL ŞABLONU - MONTE CARLO RİSK SİMÜLASYONU**\n"
                      f"**Piyasalara Genel Bakış:** Predictive (Öngörüsel) İstatistiksel Analiz ({iterations} İterasyon)\n"
                      f"Test Edilen İşlem Sayısı: {len(df)} (Gelecekteki {future_trades} işlem baz alınmıştır)\n"
                      f"Probability of Ruin (%20 Çöküş İhtimali): %{probability_of_ruin:.1f}\n"
                      f"Beklenen Maksimum Drawdown: %{expected_max_drawdown:.1f}\n"
                      f"Sonuç: Sistem {status} olarak sınıflandırılmıştır. Eğriler ekteki grafikte sunulmuştur.")

            return report, filename

        except Exception as e:
            logger.error(f"Monte Carlo hatası: {e}")
            return "Simülasyon başarısız.", None
