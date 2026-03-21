import yfinance as yf
from config.settings import Config
import logging

logger = logging.getLogger(__name__)

class SymbolUniverse:
    def __init__(self):
        self.symbols = Config.BIST30_SYMBOLS.copy()

    def get_symbols(self):
        return self.symbols

    def map_symbol(self, symbol, source="tv"):
        """
        Maps symbol 'THYAO' to 'BIST:THYAO' for tvdatafeed or 'THYAO.IS' for yfinance.
        """
        if source.lower() == "tv":
            return f"BIST:{symbol}"
        elif source.lower() == "yf":
            return f"{symbol}.IS"
        else:
            return symbol

    def update_universe_by_volume(self):
        """
        Updates the universe based on top 40 BIST100 stocks by 30-day average volume using yfinance.
        Since we don't have a static BIST100 list, we'll use a large enough proxy or just
        assume BIST100 components are fetched (for this mock, we'll try top 40 from a list).
        """
        logger.info("Updating universe by volume...")
        # A static list of common BIST100 for volume filtering (simplified for now).
        # In a real scenario, this list would be populated by a web scraper or an API.
        bist100_proxy = [
            "AKBNK", "ALARK", "ARCLK", "ASELS", "ASTOR", "BIMAS", "BRSAN", "CWISE",
            "EKGYO", "ENKAI", "EREGL", "FROTO", "GARAN", "GUBRF", "HEKTS", "ISCTR",
            "KCHOL", "KONTR", "KOZAA", "KOZAL", "KRDMD", "ODAS", "OYAKC", "PETKM",
            "PGSUS", "SAHOL", "SASA", "SISE", "TCELL", "THYAO", "TOASO", "TUPRS", "YKBNK",
            "ZOREN", "ISMEN", "TTKOM", "KORDS", "VESBE", "DOHOL", "TKFEN", "SOKM", "MGROS",
            "TAVHL", "ALBRK", "TSKB", "ENJSA", "AKSA", "AYDEM", "GWIND", "EGEEN", "OTKAR"
        ]

        volume_dict = {}
        for sym in bist100_proxy:
            yf_sym = self.map_symbol(sym, source="yf")
            try:
                # Fetch history for last 30 days
                ticker = yf.Ticker(yf_sym)
                hist = ticker.history(period="1mo")

                if not hist.empty and 'Volume' in hist.columns:
                    avg_volume = hist['Volume'].mean()
                    volume_dict[sym] = avg_volume
            except Exception as e:
                logger.warning(f"Failed to fetch volume for {sym}: {e}")

        # Sort by volume descending and take top 40
        sorted_symbols = sorted(volume_dict.items(), key=lambda item: item[1], reverse=True)
        top_40 = [item[0] for item in sorted_symbols[:40]]

        if top_40:
             self.symbols = top_40
             logger.info(f"Universe updated to top 40 by volume: {self.symbols}")
        else:
             logger.warning("Volume update failed. Falling back to BIST30 defaults.")
