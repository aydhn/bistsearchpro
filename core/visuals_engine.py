import mplfinance as mpf
import matplotlib
import pandas as pd
import os
import uuid

# Sunucu/arka plan süreçlerinde çökmeyi engellemek için 'Agg' backend kullanıyoruz.
matplotlib.use('Agg')

from core.logger_engine import LoggerEngine
from config.config_manager import ConfigManager

logger = LoggerEngine.get_system_logger()
os.makedirs("temp_charts", exist_ok=True)

class VisualsEngine:
    @staticmethod
    def generate_chart(df: pd.DataFrame, symbol: str, signal_index=-1) -> str:
        """
        Headless (arayüzsüz) çizim motoru.
        Admin'in (yöneticinin) görsel teyit almasını, Slippage (zaman kaybı) yaratmadan sağlar.
        """
        if df is None or len(df) < 50:
            logger.warning(f"Görsel oluşturmak için yeterli veri yok: {symbol}")
            return None

        # Son 100 barı kırp
        plot_df = df.iloc[-100:].copy()

        # Eğer indeks datetime değilse, dönüştür (mplfinance şart koşar)
        if not isinstance(plot_df.index, pd.DatetimeIndex):
            plot_df.index = pd.to_datetime(plot_df.index)

        # EMA'ları subplot olarak ekle
        ap0 = [
            mpf.make_addplot(plot_df['EMA_short'], color='blue', width=0.7),
            mpf.make_addplot(plot_df['EMA_long'], color='orange', width=0.7)
        ]

        # Alt panele RSI ekle
        ap1 = [mpf.make_addplot(plot_df['RSI'], panel=1, color='purple', secondary_y=False)]

        # Sinyal İşaretleme (Marker)
        # Sadece son muma veya `signal_index`'e yeşil ok koyarız.
        signal_markers = [float('nan')] * len(plot_df)
        signal_markers[-1] = plot_df['low'].iloc[-1] * 0.99  # Mumun hemen altına
        ap_signal = mpf.make_addplot(signal_markers, type='scatter', markersize=200, marker='^', color='green')

        all_plots = ap0 + ap1 + [ap_signal]

        # Dosya adı ve kaydetme
        filename = f"temp_charts/{symbol}_{uuid.uuid4().hex[:8]}.png"

        # Mplfinance figür ayarları
        mc = mpf.make_marketcolors(up='g', down='r', inherit=True)
        s  = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=False)

        try:
            mpf.plot(plot_df, type='candle', style=s, addplot=all_plots,
                     volume=False, figscale=1.5, title=f"{symbol} Teknik Görünüm",
                     savefig=dict(fname=filename, dpi=100, bbox_inches='tight'))

            logger.info(f"Görsel oluşturuldu: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Grafik çizim hatası ({symbol}): {e}")
            return None
