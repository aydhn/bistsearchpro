import unittest
import pandas as pd
from unittest.mock import patch, MagicMock
from core.brain import Orchestrator

class TestBrain(unittest.TestCase):
    @patch('core.brain.TurkishSentimentAnalyzer')
    @patch('core.brain.TrendFollowingEngine')
    @patch('core.brain.MeanReversionEngine')
    @patch('core.brain.StatArbEngine')
    def test_evaluate_signals_empty_df(self, mock_stat_arb, mock_reversion, mock_trend, mock_sentiment):
        # Initialize orchestrator with mocked components to avoid external dependencies or heavy initialization
        orchestrator = Orchestrator()

        # Test None
        with self.assertLogs('core.brain', level='WARNING') as cm:
            result = orchestrator.evaluate_signals("THYAO", None)
            self.assertIsNone(result)
            self.assertTrue(any("boş veri geldi" in output for output in cm.output))

        # Test empty DataFrame
        with self.assertLogs('core.brain', level='WARNING') as cm:
            result = orchestrator.evaluate_signals("THYAO", pd.DataFrame())
            self.assertIsNone(result)
            self.assertTrue(any("boş veri geldi" in output for output in cm.output))

if __name__ == '__main__':
    unittest.main()
