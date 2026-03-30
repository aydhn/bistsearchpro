import mplfinance as mpf
import pandas as pd
import os
import matplotlib
import uuid

# Sunucu/arka plan süreçlerinde (Headless GUI) çizim yapmak için 'Agg' backend'i şarttır!
matplotlib.use('Agg')

class VisualsEngine:
    """
    Slippage (zaman kaybı) yaratmadan hızlı görsel teyit sağlayan Headless Çizim Motoru (Phase 19).
    Ayrıca Monte Carlo simülasyon grafikleri için entegrasyon (Phase 21).
    """
    def __init__(self, temp_dir="temp_charts"):
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)

    def create_signal_chart(self, symbol: str, df: pd.DataFrame, ema_short: int, ema_long: int) -> str:
        """
        Son 100 barı Mum Grafik (Candlestick) + EMA + RSI alt panel ile çizer.
        Geçici .png dosya yolunu döndürür.
        """
        try:
            # Sadece son 100 barı al (Görsel kirliliği önlemek için)
            plot_df = df.tail(100).copy()

            # mplfinance indeksin DatetimeIndex olmasını bekler
            if not isinstance(plot_df.index, pd.DatetimeIndex):
                # yfinance genellikle Date sütunu döner, eğer yoksa reset_index varsayımı
                plot_df.index = pd.to_datetime(plot_df.index)

            # Ek çizimler (EMA ve RSI)
            apds = [
                mpf.make_addplot(plot_df[f'ema_{ema_short}'], color='blue', width=1.5),
                mpf.make_addplot(plot_df[f'ema_{ema_long}'], color='red', width=2.0),
                mpf.make_addplot(plot_df['rsi'], panel=1, color='purple', ylabel='RSI')
            ]

            # Son barı (sinyal barı) işaretlemek için boş bir liste oluştur
            marker_col = [float('nan')] * len(plot_df)
            marker_col[-1] = plot_df['low'].iloc[-1] * 0.98 # Mumun biraz altına ok koy
            apds.append(mpf.make_addplot(marker_col, type='scatter', markersize=200, marker='^', color='green'))

            file_name = f"{symbol}_{uuid.uuid4().hex[:8]}.png"
            file_path = os.path.join(self.temp_dir, file_name)

            # Çizimi kaydet
            mpf.plot(plot_df, type='candle', addplot=apds, style='yahoo',
                     title=f"{symbol} Sinyal Doğrulama",
                     ylabel='Fiyat', ylabel_lower='RSI',
                     volume=True, savefig=file_path)

            return file_path
        except Exception as e:
            print(f"Görsel oluşturma hatası: {e}")
            return None

    def create_monte_carlo_chart(self, simulations_matrix) -> str:
        """Monte Carlo getiri eğrilerini (Spaghetti Chart) çizer"""
        import matplotlib.pyplot as plt
        try:
            file_name = f"MC_{uuid.uuid4().hex[:8]}.png"
            file_path = os.path.join(self.temp_dir, file_name)

            plt.figure(figsize=(10, 6))
            # Her bir paralel evreni %10 opaklık (alpha=0.1) ile çiz
            for i in range(len(simulations_matrix)):
                 plt.plot(simulations_matrix[i], color='gray', alpha=0.1)

            # Ortalama (Beklenen) Getiri Çizgisi
            expected_curve = simulations_matrix.mean(axis=0)
            plt.plot(expected_curve, color='blue', linewidth=3, label='Beklenen (Ortalama) Getiri')

            # Başlangıç kasası çizgisi
            plt.axhline(y=1.0, color='red', linestyle='--', label='Başlangıç Bakiyesi')

            plt.title('Monte Carlo Risk Simülasyonu (1000 İterasyon)')
            plt.xlabel('Gelecekteki İşlem Sayısı')
            plt.ylabel('Kümülatif Getiri Çarpanı')
            plt.legend()

            plt.savefig(file_path)
            plt.close()
            return file_path
        except Exception as e:
            print(f"MC Çizim Hatası: {e}")
            return None
