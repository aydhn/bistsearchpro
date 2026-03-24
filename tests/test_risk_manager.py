import unittest
from unittest.mock import patch
from core.risk_manager import RiskManager

class TestRiskManager(unittest.TestCase):
    def test_calculate_position_size_invalid_stop_loss(self):
        # Case where stop_loss >= entry_price (for LONG only)
        # current_balance=10000, entry_price=100, stop_loss=105, take_profit=120
        with self.assertLogs('core.risk_manager', level='WARNING') as cm:
            result = RiskManager.calculate_position_size(10000, 100, 105, 120)
            self.assertEqual(result, 0)
            self.assertTrue(any("Stop-Loss seviyesi giriş fiyatından büyük veya eşit olamaz" in output for output in cm.output))

    def test_calculate_position_size_invalid_inputs(self):
        # Invalid current_balance (<= 0)
        with self.assertLogs('core.risk_manager', level='ERROR') as cm:
            result = RiskManager.calculate_position_size(0, 100, 95, 110)
            self.assertEqual(result, 0)
            self.assertTrue(any("Geçersiz bakiye veya giriş fiyatı" in output for output in cm.output))

        # Invalid entry_price (<= 0)
        with self.assertLogs('core.risk_manager', level='ERROR') as cm:
            result = RiskManager.calculate_position_size(10000, 0, 95, 110)
            self.assertEqual(result, 0)
            self.assertTrue(any("Geçersiz bakiye veya giriş fiyatı" in output for output in cm.output))

    def test_calculate_position_size_happy_path(self):
        # Valid inputs
        # balance=10000, entry=100, sl=95, tp=110
        # risk_per_share = 100 - 95 = 5
        # reward_per_share = 110 - 100 = 10
        # risk_reward_ratio = 10 / 5 = 2.0
        # max_risk_amount = 10000 * 0.02 = 200
        # max_lot_fixed = 200 / 5 = 40
        # Kelly: half_kelly = (0.55 - (0.45 / 2.0)) / 2 = (0.55 - 0.225) / 2 = 0.325 / 2 = 0.1625
        # lot_kelly = floor(10000 * 0.1625 / 100) = floor(16.25) = 16
        # final_lot = min(40, 16) = 16
        # affordable = floor(10000 / 100) = 100
        # final_lot = min(16, 100) = 16

        result = RiskManager.calculate_position_size(10000, 100, 95, 110)
        self.assertEqual(result, 16)

if __name__ == '__main__':
    unittest.main()
