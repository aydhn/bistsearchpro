import unittest
from unittest.mock import AsyncMock, MagicMock
from core.circuit_breaker import CircuitBreaker

class TestCircuitBreaker(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_state_manager = MagicMock()
        self.mock_notifier = MagicMock()
        self.mock_trader = MagicMock()

        self.circuit_breaker = CircuitBreaker(
            state_manager=self.mock_state_manager,
            notifier=self.mock_notifier,
            paper_trader=self.mock_trader
        )

    async def test_record_failure_increments_counter(self):
        self.circuit_breaker._trigger_halt = AsyncMock()

        await self.circuit_breaker.record_failure()
        self.assertEqual(self.circuit_breaker.consecutive_failures, 1)
        self.circuit_breaker._trigger_halt.assert_not_called()

    async def test_record_failure_triggers_halt(self):
        self.circuit_breaker._trigger_halt = AsyncMock()

        # 1. Başarısızlık
        await self.circuit_breaker.record_failure()
        self.circuit_breaker._trigger_halt.assert_not_called()

        # 2. Başarısızlık
        await self.circuit_breaker.record_failure()
        self.circuit_breaker._trigger_halt.assert_not_called()

        # 3. Başarısızlık (Maksimum limite ulaşılır ve halt tetiklenmeli)
        await self.circuit_breaker.record_failure()

        self.assertEqual(self.circuit_breaker.consecutive_failures, 3)
        self.circuit_breaker._trigger_halt.assert_awaited_once_with("Ardışık 3 analiz döngüsünde veri çekilemedi veya hata alındı.")

if __name__ == '__main__':
    unittest.main()
