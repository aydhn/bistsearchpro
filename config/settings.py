import os

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
    CHAT_ID = os.getenv("CHAT_ID", "")

    BIST30_SYMBOLS = [
        "AKBNK", "ALARK", "ARCLK", "ASELS", "ASTOR", "BIMAS", "BRSAN", "CWISE",
        "EKGYO", "ENKAI", "EREGL", "FROTO", "GARAN", "GUBRF", "HEKTS", "ISCTR",
        "KCHOL", "KONTR", "KOZAA", "KOZAL", "KRDMD", "ODAS", "OYAKC", "PETKM",
        "PGSUS", "SAHOL", "SASA", "SISE", "TCELL", "THYAO", "TOASO", "TUPRS", "YKBNK"
    ]

    MAX_RISK_PER_TRADE = 0.02 # 2% of total capital

    # Paths
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    DB_PATH = os.path.join(DATA_DIR, "market_data.db")
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

config = Config()
