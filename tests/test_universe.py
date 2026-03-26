import unittest
from unittest.mock import MagicMock
from core.universe import SymbolUniverse

class TestUniverse(unittest.TestCase):
    def test_base_symbols(self):
        mock_fetcher = MagicMock()
        mock_db = MagicMock()
        universe = SymbolUniverse(mock_fetcher, mock_db)

        self.assertIn("THYAO", universe.base_symbols)

if __name__ == '__main__':
    unittest.main()
