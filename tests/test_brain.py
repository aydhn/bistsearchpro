import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from core.brain import Orchestrator
from strategies.signal_trend import SignalResponse

class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.orchestrator = Orchestrator()
        self.dummy_df = pd.DataFrame({'close': [100, 105], 'ema_20': [98, 102]})
        self.symbol = "TEST"

    def test_evaluate_signals_empty_df(self):
        # Should return None and log a warning
        result = self.orchestrator.evaluate_signals(self.symbol, pd.DataFrame())
        self.assertIsNone(result)

        result_none = self.orchestrator.evaluate_signals(self.symbol, None)
        self.assertIsNone(result_none)

    @patch('core.brain.MacroFilter.get_macro_risk_flag')
    def test_evaluate_signals_macro_veto(self, mock_macro):
        mock_macro.return_value = True
        result = self.orchestrator.evaluate_signals(self.symbol, self.dummy_df)
        self.assertIsNone(result)
        mock_macro.assert_called_once()

    @patch('core.brain.MacroFilter.get_macro_risk_flag')
    @patch.object(Orchestrator, '__init__', lambda x: None) # Patch init if we wanted to mock analyzer entirely, but let's mock the instance method
    def test_evaluate_signals_sentiment_veto(self, mock_macro):
        mock_macro.return_value = False

        # We need a fresh orchestrator to mock its instance attribute
        orchestrator = Orchestrator()
        orchestrator.sentiment_analyzer = MagicMock()
        orchestrator.sentiment_analyzer.analyze.return_value = -0.6

        result = orchestrator.evaluate_signals(self.symbol, self.dummy_df, news_headline="Çok kötü haber")
        self.assertIsNone(result)
        orchestrator.sentiment_analyzer.analyze.assert_called_once_with("Çok kötü haber")

    @patch('core.brain.MacroFilter.get_macro_risk_flag')
    @patch('core.brain.RegimeFilter.determine_regime')
    def test_evaluate_signals_no_regime(self, mock_regime, mock_macro):
        mock_macro.return_value = False
        mock_regime.return_value = None

        result = self.orchestrator.evaluate_signals(self.symbol, self.dummy_df)
        self.assertIsNone(result)

    @patch('core.brain.MacroFilter.get_macro_risk_flag')
    @patch('core.brain.RegimeFilter.determine_regime')
    def test_evaluate_signals_no_signals(self, mock_regime, mock_macro):
        mock_macro.return_value = False
        mock_regime.return_value = {'regime': 'REGIME_TREND', 'direction': 'BULL'}

        orchestrator = Orchestrator()
        orchestrator.trend_engine = MagicMock()
        orchestrator.trend_engine.generate_signal.return_value = None
        orchestrator.reversion_engine = MagicMock()
        orchestrator.reversion_engine.generate_signal.return_value = None

        result = orchestrator.evaluate_signals(self.symbol, self.dummy_df)
        self.assertIsNone(result)

    @patch('core.brain.MacroFilter.get_macro_risk_flag')
    @patch('core.brain.RegimeFilter.determine_regime')
    def test_evaluate_signals_successful_selection(self, mock_regime, mock_macro):
        mock_macro.return_value = False
        regime_info = {'regime': 'REGIME_TREND', 'direction': 'BULL'}
        mock_regime.return_value = regime_info

        orchestrator = Orchestrator()

        trend_sig = SignalResponse(
            symbol=self.symbol, direction="BUY", entry_price=105,
            stop_loss=100, take_profit=115, confidence_score=75.0, strategy_name="TrendFollowing"
        )
        orchestrator.trend_engine = MagicMock()
        orchestrator.trend_engine.generate_signal.return_value = trend_sig

        reversion_sig = SignalResponse(
            symbol=self.symbol, direction="BUY", entry_price=105,
            stop_loss=100, take_profit=110, confidence_score=85.0, strategy_name="MeanReversion"
        )
        orchestrator.reversion_engine = MagicMock()
        orchestrator.reversion_engine.generate_signal.return_value = reversion_sig

        result = orchestrator.evaluate_signals(self.symbol, self.dummy_df)

        self.assertIsNotNone(result)
        self.assertEqual(result.strategy_name, "MeanReversion")
        self.assertEqual(result.confidence_score, 85.0)

    @patch('core.brain.MacroFilter.get_macro_risk_flag')
    @patch('core.brain.RegimeFilter.determine_regime')
    def test_evaluate_signals_sentiment_boost(self, mock_regime, mock_macro):
        mock_macro.return_value = False
        mock_regime.return_value = {'regime': 'REGIME_TREND'}

        orchestrator = Orchestrator()
        orchestrator.sentiment_analyzer = MagicMock()
        orchestrator.sentiment_analyzer.analyze.return_value = 0.4  # Positive news

        # 65 * 1.1 = 71.5 (> 70)
        trend_sig = SignalResponse(
            symbol=self.symbol, direction="BUY", entry_price=105,
            stop_loss=100, take_profit=115, confidence_score=65.0, strategy_name="TrendFollowing"
        )
        orchestrator.trend_engine = MagicMock()
        orchestrator.trend_engine.generate_signal.return_value = trend_sig

        orchestrator.reversion_engine = MagicMock()
        orchestrator.reversion_engine.generate_signal.return_value = None

        result = orchestrator.evaluate_signals(self.symbol, self.dummy_df, news_headline="İyi haber")

        self.assertIsNotNone(result)
        self.assertEqual(result.strategy_name, "TrendFollowing")
        self.assertAlmostEqual(result.confidence_score, 71.5)

    @patch('core.brain.MacroFilter.get_macro_risk_flag')
    @patch('core.brain.RegimeFilter.determine_regime')
    def test_evaluate_signals_rejected_low_confidence(self, mock_regime, mock_macro):
        mock_macro.return_value = False
        mock_regime.return_value = {'regime': 'REGIME_TREND'}

        orchestrator = Orchestrator()

        # 60 < 70, no sentiment boost
        trend_sig = SignalResponse(
            symbol=self.symbol, direction="BUY", entry_price=105,
            stop_loss=100, take_profit=115, confidence_score=60.0, strategy_name="TrendFollowing"
        )
        orchestrator.trend_engine = MagicMock()
        orchestrator.trend_engine.generate_signal.return_value = trend_sig

        orchestrator.reversion_engine = MagicMock()
        orchestrator.reversion_engine.generate_signal.return_value = None

        result = orchestrator.evaluate_signals(self.symbol, self.dummy_df)

        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
