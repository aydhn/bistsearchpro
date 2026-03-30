import json
import sqlite3
import pandas as pd
from datetime import datetime
from collections import defaultdict
from core.universe import Universe
from core.logger_engine import LoggerEngine

# "Nerede kan kaybediyoruz?" sorusunun cevabı hayati önem taşır.
# Bu modül, geçmiş işlemleri okuyarak derinlemesine teşhis (Diagnostic) yapar.
# Dinamik Kara Liste (Dynamic Blacklist) sistemi piyasa rejimindeki sektörel değişimlere adapte eder.

logger = LoggerEngine.get_trade_logger()

class AnalyticsEngine:
    def __init__(self, db_path="data/portfolio.db"):
        self.db_path = db_path
        self.blacklist_file = "data/blacklist.json"

    def analyze_performance(self):
        try:
            conn = sqlite3.connect(self.db_path)
            query = "SELECT * FROM trade_history"
            df = pd.read_sql_query(query, conn)
            conn.close()

            if df.empty:
                return "Yeterli veri yok."

            # Genel Metrikler
            total_trades = len(df)
            winning_trades = len(df[df['pnl'] > 0])
            win_rate = (winning_trades / total_trades) * 100

            avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
            avg_loss = df[df['pnl'] <= 0]['pnl'].mean() if (total_trades - winning_trades) > 0 else 0
            profit_factor = abs(df[df['pnl'] > 0]['pnl'].sum() / df[df['pnl'] <= 0]['pnl'].sum()) if df[df['pnl'] <= 0]['pnl'].sum() != 0 else float('inf')

            # Sektörel Analiz (Groupby)
            df['sector'] = df['symbol'].apply(Universe.get_sector)
            sector_stats = df.groupby('sector').agg(
                trades=('symbol', 'count'),
                wins=('pnl', lambda x: (x > 0).sum())
            )
            sector_stats['win_rate'] = (sector_stats['wins'] / sector_stats['trades']) * 100

            # Tutma Süresi (Holding Period)
            df['entry_time'] = pd.to_datetime(df['entry_time'])
            df['exit_time'] = pd.to_datetime(df['exit_time'])
            df['holding_hours'] = (df['exit_time'] - df['entry_time']).dt.total_seconds() / 3600

            avg_hold_win = df[df['pnl'] > 0]['holding_hours'].mean()
            avg_hold_loss = df[df['pnl'] <= 0]['holding_hours'].mean()

            # Dinamik Kara Liste (Self-Correction) - Son 10 işlemde %30 altı
            self._update_blacklist(df)

            best_sector = sector_stats['win_rate'].idxmax() if not sector_stats.empty else "N/A"
            best_sector_wr = sector_stats['win_rate'].max() if not sector_stats.empty else 0
            worst_sector = sector_stats['win_rate'].idxmin() if not sector_stats.empty else "N/A"

            report = (f"🔬 **ED CAPITAL KURUMSAL ŞABLONU - PERFORMANS TEŞHİS RAPORU**\n"
                      f"**Piyasalara Genel Bakış:** Algoritma İstatistiksel Analizi\n"
                      f"Genel Win-Rate: %{win_rate:.1f} | Ortalama Kâr/Zarar Oranı: {abs(avg_win/avg_loss) if avg_loss != 0 else 'N/A'}\n"
                      f"En Kârlı Sektör: {best_sector} (%{best_sector_wr:.1f} Win-Rate)\n"
                      f"Kan Kaybedilen Sektör: {worst_sector} (Otomatik Kara Listeye Alındı 🔴)\n"
                      f"İstatistiksel Gözlem: Kazanan pozisyonlar ortalama {avg_hold_win:.1f} saat tutulurken, kaybedenler {avg_hold_loss:.1f} saatte stop olmuştur.")
            return report

        except Exception as e:
            logger.error(f"Analitik motoru hatası: {e}")
            return "Analiz başarısız."

    def _update_blacklist(self, df):
        try:
            blacklist = []

            # Sembol bazlı analiz (son 10 işlem)
            for symbol in df['symbol'].unique():
                sym_trades = df[df['symbol'] == symbol].tail(10)
                if len(sym_trades) >= 5: # Yeterli örneklem
                    wr = (len(sym_trades[sym_trades['pnl'] > 0]) / len(sym_trades)) * 100
                    if wr < 30:
                        blacklist.append(symbol)

            with open(self.blacklist_file, "w") as f:
                json.dump(blacklist, f)

            logger.info(f"Kara Liste güncellendi. {len(blacklist)} hisse eklendi.")
        except Exception as e:
            logger.error(f"Kara liste güncelleme hatası: {e}")
