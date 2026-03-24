import unittest
from unittest.mock import Mock
from core.circuit_breaker import CircuitBreaker

class TestCircuitBreaker(unittest.TestCase):
    def setUp(self):
        # Create mock dependencies
        self.mock_state_manager = Mock()
        self.mock_notifier = Mock()
        self.mock_trader = Mock()

        # Instantiate CircuitBreaker with mocks
        self.circuit_breaker = CircuitBreaker(
            state_manager=self.mock_state_manager,
            notifier=self.mock_notifier,
            paper_trader=self.mock_trader
        )

    def test_record_success_resets_failures(self):
        # Arrange: Set consecutive_failures > 0
        self.circuit_breaker.consecutive_failures = 2

        # Act: Call record_success
        with self.assertLogs('core.circuit_breaker', level='INFO') as cm:
            self.circuit_breaker.record_success()

        # Assert: consecutive_failures should be 0, and a log message should be emitted
        self.assertEqual(self.circuit_breaker.consecutive_failures, 0)
        self.assertTrue(any("Döngü başarılı, hata sayacı sıfırlanıyor." in output for output in cm.output))

    def test_record_success_no_log_when_no_failures(self):
        # Arrange: Set consecutive_failures to 0
        self.circuit_breaker.consecutive_failures = 0

        # Act: Call record_success and assert no logs are emitted
        # We can test this by checking that assertLogs raises an AssertionError
        # because no logs with level INFO or higher were emitted.
        with self.assertRaises(AssertionError):
            with self.assertLogs('core.circuit_breaker', level='INFO'):
                self.circuit_breaker.record_success()

        # Assert: consecutive_failures remains 0
        self.assertEqual(self.circuit_breaker.consecutive_failures, 0)

if __name__ == '__main__':
    unittest.main()
