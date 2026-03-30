# BIST30 ve BIST100 hisse senetlerinin sembollerini (ticker) tutan ve yöneten bir modül.
# Tarama yapılacak evreni dinamik olarak seçmemize olanak tanır.
import json

class Universe:
    # Gerçek uygulamada İş Yatırım veya YFinance destekli .IS uzantılı liste.
    # Bu liste Sektör Konsantrasyon Filtresi için sektör bilgisiyle (dictionary) güncellenecek.

    BIST30_SECTORS = {
        "AKBNK.IS": "Bankacılık",
        "ARCLK.IS": "Sanayi",
        "ASELS.IS": "Sanayi",
        "BIMAS.IS": "Perakende",
        "EKGYO.IS": "GYO",
        "ENKAI.IS": "İnşaat",
        "EREGL.IS": "Demir Çelik",
        "FROTO.IS": "Otomotiv",
        "GARAN.IS": "Bankacılık",
        "GUBRF.IS": "Kimya",
        "HEKTS.IS": "Kimya",
        "ISCTR.IS": "Bankacılık",
        "KCHOL.IS": "Holding",
        "KOZAA.IS": "Madencilik",
        "KOZAL.IS": "Madencilik",
        "KRDMD.IS": "Demir Çelik",
        "PETKM.IS": "Kimya",
        "PGSUS.IS": "Ulaştırma",
        "SAHOL.IS": "Holding",
        "SASA.IS": "Kimya",
        "SISE.IS": "Cam",
        "TAVHL.IS": "Ulaştırma",
        "TCELL.IS": "İletişim",
        "THYAO.IS": "Ulaştırma",
        "TKFEN.IS": "İnşaat",
        "TOASO.IS": "Otomotiv",
        "TSKB.IS": "Bankacılık",
        "TTKOM.IS": "İletişim",
        "TUPRS.IS": "Enerji",
        "YKBNK.IS": "Bankacılık"
    }

    @staticmethod
    def get_bist30_symbols():
        return list(Universe.BIST30_SECTORS.keys())

    @staticmethod
    def get_sector(symbol):
        return Universe.BIST30_SECTORS.get(symbol, "Bilinmiyor")
