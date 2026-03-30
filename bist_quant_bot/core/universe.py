import yfinance as yf
import pandas as pd
import logging
from typing import List, Dict

class UniverseManager:
    """
    Tarama yapılacak evreni dinamik olarak seçmemize olanak tanır.
    İsteğe bağlı olarak sektörel sınıflandırmayı barındırır (Sektörel Konsantrasyon Filtresi için).
    Kıdemli Quant Notu: Web scraping sıfır bütçe kuralı ihlali riski taşıdığı için statik listeler veya
    ücretsiz açık kaynak (örn: BIST Wikipedia parser yerine hardcoded BIST30 listesi) kullanılır.
    Ayrıca yfinance için '.IS' uzantısı zorunludur.
    """

    # BIST30 ve sektör haritalaması
    _BIST30_SYMBOLS = {
        "AKBNK.IS": "Bankacılık",
        "ALARK.IS": "Holding",
        "ARCLK.IS": "Sanayi",
        "ASELS.IS": "Savunma",
        "BIMAS.IS": "Perakende",
        "BRISA.IS": "Sanayi",
        "CCOL.IS": "Gıda",
        "CWENE.IS": "Enerji",
        "ENKAI.IS": "İnşaat",
        "EREGL.IS": "Demir-Çelik",
        "FROTO.IS": "Otomotiv",
        "GARAN.IS": "Bankacılık",
        "GUBRF.IS": "Kimya",
        "HEKTS.IS": "Kimya",
        "ISCTR.IS": "Bankacılık",
        "KCHOL.IS": "Holding",
        "KONTRO.IS": "Teknoloji",
        "KOZAL.IS": "Madencilik",
        "KRDMD.IS": "Demir-Çelik",
        "MGROS.IS": "Perakende",
        "ODAS.IS": "Enerji",
        "PETKM.IS": "Kimya",
        "PGSUS.IS": "Ulaştırma",
        "SAHOL.IS": "Holding",
        "SASA.IS": "Kimya",
        "SISE.IS": "Cam",
        "TCELL.IS": "İletişim",
        "THYAO.IS": "Ulaştırma",
        "TOASO.IS": "Otomotiv",
        "TUPRS.IS": "Enerji",
        "YKBNK.IS": "Bankacılık"
    }

    @classmethod
    def get_bist30_symbols(cls) -> List[str]:
        return list(cls._BIST30_SYMBOLS.keys())

    @classmethod
    def get_sector_map(cls) -> Dict[str, str]:
        return cls._BIST30_SYMBOLS
