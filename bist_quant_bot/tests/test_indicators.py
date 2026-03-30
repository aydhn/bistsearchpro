import unittest
import pandas as pd
from core.indicators import IndicatorEngine

class TestIndicators(unittest.TestCase):
    def setUp(self):
        self.config = {
            'strategy_settings': {
                'EMA_SHORT': 50,
                'EMA_LONG': 200,
                'RSI_PERIOD': 14,
                'ATR_PERIOD': 14,
                'VOLATILITY_LOOKBACK': 50
            }
        }
        self.engine = IndicatorEngine(self.config)

    def test_enrich_data_empty(self):
        df = pd.DataFrame()
        res = self.engine.enrich_data(df)
        self.assertTrue(res.empty)

if __name__ == '__main__':
    unittest.main()
