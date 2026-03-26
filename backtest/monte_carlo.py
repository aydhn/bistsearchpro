import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class MonteCarloSimulator:
    """
    Monte Carlo İflas Olasılığı (Probability of Ruin) Motoru
    Olay Yönlendirmeli Backtest'ten (advanced_backtester.py) çıkan işlem listesini
    alarak, işlemlerin sırasını rastgele karıştırır (Resampling with replacement).
    10.000 farklı alternatif evren simülasyonu çalıştırarak stratejinin şans eseri
    başarılı olup olmadığını ölçer.
    """
    def __init__(self, initial_capital=100000.0, num_simulations=10000):
        self.initial_capital = initial_capital
        self.num_simulations = num_simulations

    def run_simulation(self, trade_results: list) -> dict:
        """
        trade_results: [{'pnl_pct': 0.05}, {'pnl_pct': -0.02}, ...] gibi
        yüzdelik kâr/zarar oranlarını (veya sabit TL bazlı net kâr/zararı)
        içeren liste olmalıdır.
        """
        logger.info(f"Monte Carlo Simülasyonu ({self.num_simulations} evren) başlatıldı...")

        if not trade_results or len(trade_results) < 10:
            logger.warning("Monte Carlo için yetersiz işlem sayısı.")
            return {}

        try:
            # Sadece PnL (Yüzde veya TL) dizisini al
            pnl_array = np.array([trade.get('pnl_pct', 0.0) for trade in trade_results])
            n_trades = len(pnl_array)

            # Numpy ile 10.000 adet, her biri n_trades uzunluğunda rastgele seçilmiş (replacement=True) indeks matrisi oluştur
            random_indices = np.random.choice(len(pnl_array), size=(self.num_simulations, n_trades), replace=True)

            # Seçilen indekslere karşılık gelen PnL değerlerini çek
            simulated_pnls = pnl_array[random_indices]

            # Eğer pnl_array yüzdelik getiri ise (+%5 = 0.05), her işlemi (1 + pnl) ile çarparak sermayeyi büyüt/küçült
            # Vektörel Kümülatif Çarpım (Cumulative Product)
            # shape=(10000, n_trades)
            simulated_cumulative = np.cumprod(1 + simulated_pnls, axis=1) * self.initial_capital

            # 1. İflas Olasılığı (Probability of Ruin) - Örn: Kasanın %50'sini kaybetme durumu
            ruin_threshold = self.initial_capital * 0.50
            # Her bir simülasyon yolunda (row), bakiyenin ruin_threshold altına düşüp düşmediğini kontrol et
            ruined_simulations = np.any(simulated_cumulative < ruin_threshold, axis=1)
            probability_of_ruin = np.mean(ruined_simulations) * 100.0

            # 2. %95 Güven Aralığında Beklenen Max Drawdown
            # Her simülasyon için Maksimum Düşüşü bulalım
            rolling_max = np.maximum.accumulate(simulated_cumulative, axis=1)
            drawdowns = (simulated_cumulative - rolling_max) / rolling_max
            max_drawdowns_per_sim = np.min(drawdowns, axis=1) * 100.0  # Negatif yüzde (-%)

            # 10.000 simülasyonun Max Drawdown değerlerini sıralayıp %5'lik en kötü kesite (veya 95. persentile) bakalım
            confidence_interval_95_mdd = np.percentile(max_drawdowns_per_sim, 5) # %5 quantile (en kötü senaryoların başlangıcı)

            # Ortalama Beklenen Bitiş Bakiyesi
            expected_final_capital = np.mean(simulated_cumulative[:, -1])

            logger.info(f"Monte Carlo İflas Olasılığı (Probability of Ruin): %{probability_of_ruin:.2f}")
            logger.info(f"%95 Güven Aralığında Max Drawdown: {confidence_interval_95_mdd:.2f}%")

            return {
                "probability_of_ruin": probability_of_ruin,
                "confidence_95_max_drawdown": confidence_interval_95_mdd,
                "expected_final_capital": expected_final_capital,
                # Dashboard Spagetti Grafiği için (Çok veri olduğu için ilk 100'ünü dönebiliriz)
                "sample_equity_curves": simulated_cumulative[:100].tolist()
            }

        except Exception as e:
            logger.error(f"Monte Carlo hesaplaması sırasında hata: {str(e)}")
            return {}

    """
    [QUANT MİMARI NOTU - MONTE CARLO STRES TESTİ]
    Geçmişte elde ettiğiniz mükemmel bir büyüme eğrisi (Equity Curve), stratejinizin
    aslında berbat olduğu ama sadece o piyasa koşullarında (Örn: Boğa rallisi) ve
    o spesifik sırayla (Örn: Şans eseri 5 başarılı işlem arka arkaya geldiği)
    işlem yaptığınız için harika görünmesi kaynaklı olabilir.

    Monte Carlo simülasyonu, "Şans" ile "Gerçek İstatistiksel Avantajı" (Edge)
    birbirinden ayırır. İşlemlerinizin sırasını on binlerce kez karıştırarak,
    "En kötü şans silsilesi başıma gelseydi, kasam patlar mıydı?" sorusunu yanıtlar.
    Eğer 10.000 paralel evrenin 500'ünde kasanız %50 eriyorsa (%5 Probability of Ruin),
    sisteminizin Kelly Oranını (Lot büyüklüğünü) yarıya indirmeniz gerekir.
    """
