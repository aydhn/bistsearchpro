import pytest
from unittest.mock import patch
from telegram_bot.notifier import TelegramNotifier, CriticalError

def test_telegram_notifier_missing_token_or_chat_id():
    """Test that TelegramNotifier raises CriticalError when TELEGRAM_TOKEN or CHAT_ID is missing."""

    # Test missing token
    with patch("telegram_bot.notifier.config") as mock_config:
        mock_config.TELEGRAM_TOKEN = None
        mock_config.CHAT_ID = "123456789"

        with pytest.raises(CriticalError, match="TELEGRAM_TOKEN and CHAT_ID must be set in the environment."):
            TelegramNotifier()

    # Test missing chat_id
    with patch("telegram_bot.notifier.config") as mock_config:
        mock_config.TELEGRAM_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        mock_config.CHAT_ID = None

        with pytest.raises(CriticalError, match="TELEGRAM_TOKEN and CHAT_ID must be set in the environment."):
            TelegramNotifier()

    # Test empty string token
    with patch("telegram_bot.notifier.config") as mock_config:
        mock_config.TELEGRAM_TOKEN = ""
        mock_config.CHAT_ID = "123456789"

        with pytest.raises(CriticalError, match="TELEGRAM_TOKEN and CHAT_ID must be set in the environment."):
            TelegramNotifier()

    # Test empty string chat_id
    with patch("telegram_bot.notifier.config") as mock_config:
        mock_config.TELEGRAM_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        mock_config.CHAT_ID = ""

        with pytest.raises(CriticalError, match="TELEGRAM_TOKEN and CHAT_ID must be set in the environment."):
            TelegramNotifier()
