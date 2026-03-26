import streamlit as st
import pandas as pd
import sqlite3
import os
import matplotlib.pyplot as plt

# Proje Kök Dizini ve Veritabanı Yolu
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'market_data.db')

# Streamlit Sayfa Yapılandırması
st.set_page_config(page_title="BIST Quant Alpha", page_icon="📈", layout="wide")

def load_data(query):
    """Veritabanından salt okunur veri çeker."""
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Veritabanı bağlantı hatası: {e}")
        return pd.DataFrame()

# Ana Başlık
st.title("📈 BIST Quant Alpha - Komuta Merkezi")
st.markdown("---")

# 4 Ana Panel
col1, col2 = st.columns(2)

with col1:
    # Panel 1: Piyasalara Genel Bakış & Rejim
    st.subheader("🌍 Piyasa Rejimi & Durum")
    # Bu veriler normalde state'ten veya DB'den okunur. Şimdilik mock veya trade_journal'dan son durumu çekiyoruz.
    try:
        df_journal = load_data("SELECT * FROM trade_journal ORDER BY id DESC LIMIT 10")
        if not df_journal.empty:
            last_regime = df_journal['market_regime'].iloc[0]
            st.metric("XU100 Güncel Rejim", last_regime, delta="Boğa" if last_regime == "BULL" else "Ayı", delta_color="normal" if last_regime == "BULL" else "inverse")
            st.write(f"Son İşlem: {df_journal['symbol'].iloc[0]} ({df_journal['direction'].iloc[0]})")
        else:
            st.info("Henüz işlem kaydı yok.")
    except Exception:
        st.info("Sistem başlatılıyor...")

with col2:
    # Panel 3: Stratejik Varlık Tahsisi (Pasta Grafik)
    st.subheader("💼 Stratejik Varlık Tahsisi")
    try:
        df_open = load_data("SELECT symbol, entry_price, lot_size FROM open_positions")
        df_wallet = load_data("SELECT balance FROM paper_wallet WHERE id = 1")

        cash = df_wallet['balance'].iloc[0] if not df_wallet.empty else 100000.0

        invested = 0.0
        labels = ['Nakit']
        sizes = [cash]

        if not df_open.empty:
            for _, row in df_open.iterrows():
                val = row['entry_price'] * row['lot_size']
                invested += val
                labels.append(row['symbol'])
                sizes.append(val)

        fig1, ax1 = plt.subplots()
        ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=plt.cm.Paired.colors)
        ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        st.pyplot(fig1)

    except Exception as e:
        st.info("Varlık tahsisi verisi alınamadı.")

st.markdown("---")

col3, col4 = st.columns(2)

with col3:
    # Panel 2: Canlı PnL ve Kağıt Ticareti (Paper Trading) Özeti
    st.subheader("💰 Sanal Portföy Büyüme Eğrisi (Equity Curve)")
    try:
        df_pnl = load_data("SELECT timestamp, pnl FROM trade_journal WHERE status = 'CLOSED' ORDER BY id ASC")
        if not df_pnl.empty:
            df_pnl['cumulative_pnl'] = df_pnl['pnl'].cumsum()
            # Başlangıç bakiyesi eklenebilir ama sadece PnL değişimi de yeterli
            st.line_chart(df_pnl['cumulative_pnl'])
        else:
            st.info("Kapanmış işlem bulunmuyor.")
    except Exception:
        st.info("PnL grafiği oluşturulamadı.")

with col4:
    # Panel 4: Yapay Zeka (ML) Performans Özeti
    st.subheader("🤖 Yapay Zeka Performans Özeti")
    try:
        df_ml = load_data("SELECT ml_prob, pnl FROM trade_journal WHERE status = 'CLOSED' AND ml_prob > 0 ORDER BY id DESC LIMIT 30")
        if not df_ml.empty:
            # Başarılı sayılanlar (PnL > 0)
            success_count = len(df_ml[df_ml['pnl'] > 0])
            total_count = len(df_ml)
            accuracy = (success_count / total_count) * 100

            st.metric("Model Gerçek Başarı Oranı (Son 30 İşlem)", f"%{accuracy:.1f}")

            # Ortalama Beklenen Kazanma Oranı
            avg_prob = df_ml['ml_prob'].mean()
            st.metric("Ortalama Beklenen Kazanma Oranı", f"%{avg_prob:.1f}")

        else:
            st.info("ML performans verisi için yeterli kapanmış işlem yok.")
    except Exception:
        st.info("Yapay Zeka performansı yüklenemedi.")

st.markdown("---")
st.markdown("*(Read-Only Dashboard) Bu arayüz doğrudan yerel SQLite veritabanına bağlıdır ve sistemi bloke etmez.*")

"""
[QUANT MİMARI NOTU - GÖRSEL MONİTÖRLEME (DASHBOARD)]
Algoritmik ticarette "Black Box" (Kara Kutu) sendromu, yatırımcının sisteme olan
güvenini sarsan en büyük unsurdur. Sistem bir haftadır sürekli Stop-Loss oluyorsa,
kodların derinliklerinde bir hata mı var yoksa piyasa Ayı rejimine (Bear Market) mi
girdi sorusunun cevabı saniyeler içinde ekranda görülmelidir.

Görsel monitörleme, bir fon yöneticisinin psikolojik sermayesini (Psychological Capital)
Drawdown (sermaye erimesi) dönemlerinde koruyan tek araçtır. İşlemlerinizin %55'inin
kârla kapanıp %45'inin zararla kapanacağını (Win Rate) biliyorsanız, art arda gelen
4 zararlı işlem sizi panik yapıp "Kill Switch"e basmaya itmez.
Bu dashboard, makineye güvenmenizi sağlayan bir şeffaflık köprüsüdür.
"""
