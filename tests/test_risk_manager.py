import unittest
from unittest.mock import patch, MagicMock
from core.risk_manager import RiskManager

class TestRiskManager(unittest.TestCase):

    def setUp(self):
        self.rm = RiskManager()

    def test_calculate_trade_parameters_happy(self):
        valid, sl, tp = self.rm.calculate_trade_parameters(100.0, 2.0, "LONG")
        self.assertTrue(valid)
        self.assertEqual(sl, 97.0)
        self.assertEqual(tp, 106.0)

    def test_calculate_trade_parameters_invalid(self):
        valid, sl, tp = self.rm.calculate_trade_parameters(100.0, 0.0, "LONG")
        self.assertFalse(valid)

    def test_evaluate_dynamic_exit_breakeven(self):
        # current 103, entry 100, current_sl 97, current_tp 106, atr 2 -> Breakeven 100 + 1.0*2 = 102
        res = self.rm.evaluate_dynamic_exit("THYAO", 102.0, 100.0, 97.0, 106.0, "", 2.0, 10, "LONG")
        self.assertEqual(res['action'], 'UPDATE_SL')
        self.assertEqual(res['new_sl'], 100.0)

    def test_evaluate_dynamic_exit_trailing(self):
        # current 110, entry 100, current_sl 100, atr 2 -> tp1 = 100 + 2.0*2 = 104
        # current 110 > 104 -> partial close
        res = self.rm.evaluate_dynamic_exit("THYAO", 110.0, 100.0, 100.0, 150.0, "", 2.0, 10, "LONG")
        self.assertEqual(res['action'], 'PARTIAL_CLOSE')
        self.assertEqual(res['new_sl'], 107.0) # 110 - 1.5*2 = 107

    def test_calculate_position_size(self):
        # balance 10000, entry 100, sl 95 (risk per share = 5)
        # max_risk = 10000 * 0.02 = 200
        # shares = 200 / 5 = 40
        result = self.rm.calculate_position_size(10000.0, 100.0, 95.0)
        self.assertEqual(result, 40)

if __name__ == '__main__':
    unittest.main()
