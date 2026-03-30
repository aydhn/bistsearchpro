import unittest
import pandas as pd
from core.market_filter import MarketFilter

class TestMarketFilter(unittest.TestCase):
    def setUp(self):
        self.config = {
            'strategy_settings': {
                'EMA_LONG': 50
            }
        }
        self.filter = MarketFilter(self.config)

    def test_risk_off_empty_df(self):
        df = pd.DataFrame()
        self.assertFalse(self.filter.is_risk_on(df))

    def test_risk_on_healthy(self):
        df = pd.DataFrame({'close': [100, 101, 102, 105, 110]})
        self.assertTrue(self.filter.is_risk_on(df))

    def test_risk_off_flash_crash(self):
        df = pd.DataFrame({'close': [100, 100, 100, 100, 95]})
        self.assertFalse(self.filter.is_risk_on(df))

if __name__ == '__main__':
    unittest.main()
