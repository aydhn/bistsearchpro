import pandas as pd
import json
import os
import logging

class AnalyticsEngine:
    """
    Performans Analitiği, Feedback Loop ve Dinamik Kara Liste (Phase 16).
    Kapanan işlemleri teşhis (Diagnostic) edip zayıf sektör/hisseleri otomatik engeller.
    """
    def __init__(self, db_path="data/portfolio.db"):
        self.db_path = db_path
        self.blacklist_path = "data/blacklist.json"

    def analyze_performance(self):
        """
        Kapanan işlemleri (trade_history) okuyup win-rate analizi yapar.
        Win-rate'i %30'un altında olanları (en az 5 işlemde) kara listeye alır.
        """
        import sqlite3
        if not os.path.exists(self.db_path):
            return "Veri yok."

        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("SELECT * FROM trade_history", conn)

        if df.empty:
            return "İşlem geçmişi boş. Teşhis için yeterli veri yok."

        # Win-Rate hesaplama (Net Profit > 0 olanlar)
        df['win'] = df['net_profit'] > 0
        stats = df.groupby('symbol').agg(
            total_trades=('id', 'count'),
            win_rate=('win', 'mean')
        ).reset_index()

        # %'ye çevir
        stats['win_rate'] = stats['win_rate'] * 100

        # Kara Liste Tespiti (5 işlemden fazla, %30'dan düşük win-rate)
        toxic_symbols = stats[(stats['total_trades'] >= 5) & (stats['win_rate'] < 30)]['symbol'].tolist()

        # Blacklist'e yaz
        if toxic_symbols:
            self._update_blacklist(toxic_symbols)
            logging.warning(f"DİNAMİK KARA LİSTE GÜNCELLEMESİ: {toxic_symbols} (Sistem kendini korumaya aldı)")

        return stats.to_dict(orient='records')

    def _update_blacklist(self, symbols: list):
        # Atomik JSON yazma
        temp_path = f"{self.blacklist_path}.tmp"
        with open(temp_path, 'w') as f:
            json.dump(symbols, f)
        os.replace(temp_path, self.blacklist_path)
