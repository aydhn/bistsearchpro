import unittest
import sys
import os
import importlib.util
from unittest.mock import patch, MagicMock, AsyncMock

# Remove the current directory from sys.path temporarily to import the pip 'telegram' package
current_dir = os.path.abspath(os.curdir)
if current_dir in sys.path:
    sys.path.remove(current_dir)
if '' in sys.path:
    sys.path.remove('')

import telegram

# Now restore sys.path and load our local module dynamically
sys.path.insert(0, current_dir)

import config.settings

spec = importlib.util.spec_from_file_location("telegram.notifier", os.path.join(current_dir, "telegram", "notifier.py"))
telegram_notifier = importlib.util.module_from_spec(spec)
sys.modules["telegram.notifier"] = telegram_notifier
spec.loader.exec_module(telegram_notifier)

TelegramNotifier = telegram_notifier.TelegramNotifier
CriticalError = telegram_notifier.CriticalError

class TestTelegramNotifier(unittest.IsolatedAsyncioTestCase):
    @patch.object(telegram_notifier, 'config')
    @patch.object(telegram_notifier, 'Bot')
    def test_init_success(self, mock_bot, mock_config):
        mock_config.TELEGRAM_TOKEN = "dummy_token"
        mock_config.CHAT_ID = "dummy_chat_id"

        notifier = TelegramNotifier()
        self.assertEqual(notifier.token, "dummy_token")
        self.assertEqual(notifier.chat_id, "dummy_chat_id")
        mock_bot.assert_called_once_with(token="dummy_token")

    @patch.object(telegram_notifier, 'config')
    def test_init_missing_token(self, mock_config):
        mock_config.TELEGRAM_TOKEN = ""
        mock_config.CHAT_ID = "dummy_chat_id"

        with self.assertRaises(CriticalError):
            TelegramNotifier()

    @patch.object(telegram_notifier, 'config')
    def test_init_missing_chat_id(self, mock_config):
        mock_config.TELEGRAM_TOKEN = "dummy_token"
        mock_config.CHAT_ID = ""

        with self.assertRaises(CriticalError):
            TelegramNotifier()

    @patch.object(telegram_notifier, 'config')
    @patch.object(telegram_notifier, 'Bot')
    async def test_send_signal_success(self, mock_bot_class, mock_config):
        mock_config.TELEGRAM_TOKEN = "dummy_token"
        mock_config.CHAT_ID = "dummy_chat_id"

        mock_bot_instance = AsyncMock()
        mock_bot_class.return_value = mock_bot_instance

        notifier = TelegramNotifier()

        await notifier.send_signal("THYAO", "BUY", 100.5, 95.0, 110.0, 85)

        mock_bot_instance.send_message.assert_called_once()
        call_args = mock_bot_instance.send_message.call_args[1]

        self.assertEqual(call_args['chat_id'], "dummy_chat_id")
        self.assertEqual(call_args['parse_mode'], "MarkdownV2")
        self.assertIn("*THYAO* Sinyali", call_args['text'])
        self.assertIn(r"Yön: 🟢 LONG", call_args['text'])
        self.assertIn(r"Giriş Fiyatı: 100\.5", call_args['text'])
        self.assertIn(r"Stop Loss: 95\.0", call_args['text'])
        self.assertIn(r"Take Profit: 110\.0", call_args['text'])
        self.assertIn(r"Güven Skoru: 85%", call_args['text'])

    @patch.object(telegram_notifier, 'config')
    @patch.object(telegram_notifier, 'Bot')
    async def test_send_signal_short(self, mock_bot_class, mock_config):
        mock_config.TELEGRAM_TOKEN = "dummy_token"
        mock_config.CHAT_ID = "dummy_chat_id"

        mock_bot_instance = AsyncMock()
        mock_bot_class.return_value = mock_bot_instance

        notifier = TelegramNotifier()

        await notifier.send_signal("GARAN", "SELL", 50.0, 55.0, 40.0, 90)

        call_args = mock_bot_instance.send_message.call_args[1]
        self.assertIn("Yön: 🔴 SHORT", call_args['text'])

    @patch.object(telegram_notifier, 'config')
    @patch.object(telegram_notifier, 'Bot')
    async def test_send_signal_exception(self, mock_bot_class, mock_config):
        mock_config.TELEGRAM_TOKEN = "dummy_token"
        mock_config.CHAT_ID = "dummy_chat_id"

        mock_bot_instance = AsyncMock()
        mock_bot_instance.send_message.side_effect = Exception("API Error")
        mock_bot_class.return_value = mock_bot_instance

        notifier = TelegramNotifier()

        with self.assertLogs('telegram.notifier', level='ERROR') as cm:
            await notifier.send_signal("THYAO", "BUY", 100.5, 95.0, 110.0, 85)
            self.assertTrue(any("Failed to send signal message: API Error" in output for output in cm.output))

    @patch.object(telegram_notifier, 'config')
    @patch.object(telegram_notifier, 'Bot')
    async def test_send_system_alert_success(self, mock_bot_class, mock_config):
        mock_config.TELEGRAM_TOKEN = "dummy_token"
        mock_config.CHAT_ID = "dummy_chat_id"

        mock_bot_instance = AsyncMock()
        mock_bot_class.return_value = mock_bot_instance

        notifier = TelegramNotifier()

        await notifier.send_system_alert("Database connection lost", level="ERROR")

        mock_bot_instance.send_message.assert_called_once()
        call_args = mock_bot_instance.send_message.call_args[1]

        self.assertEqual(call_args['chat_id'], "dummy_chat_id")
        self.assertEqual(call_args['parse_mode'], "MarkdownV2")
        self.assertIn("❌ *SİSTEM BİLDİRİMİ* ❌", call_args['text'])
        self.assertIn("Database connection lost", call_args['text'])

    @patch.object(telegram_notifier, 'config')
    @patch.object(telegram_notifier, 'Bot')
    async def test_send_system_alert_default_level(self, mock_bot_class, mock_config):
        mock_config.TELEGRAM_TOKEN = "dummy_token"
        mock_config.CHAT_ID = "dummy_chat_id"

        mock_bot_instance = AsyncMock()
        mock_bot_class.return_value = mock_bot_instance

        notifier = TelegramNotifier()

        await notifier.send_system_alert("System started")

        call_args = mock_bot_instance.send_message.call_args[1]
        self.assertIn("ℹ️ *SİSTEM BİLDİRİMİ* ℹ️", call_args['text'])

    @patch.object(telegram_notifier, 'config')
    @patch.object(telegram_notifier, 'Bot')
    async def test_send_system_alert_exception(self, mock_bot_class, mock_config):
        mock_config.TELEGRAM_TOKEN = "dummy_token"
        mock_config.CHAT_ID = "dummy_chat_id"

        mock_bot_instance = AsyncMock()
        mock_bot_instance.send_message.side_effect = Exception("Network Error")
        mock_bot_class.return_value = mock_bot_instance

        notifier = TelegramNotifier()

        with self.assertLogs('telegram.notifier', level='ERROR') as cm:
            await notifier.send_system_alert("Test alert")
            self.assertTrue(any("Failed to send system alert: Network Error" in output for output in cm.output))

    @patch.object(telegram_notifier, 'config')
    @patch.object(telegram_notifier, 'Bot')
    async def test_filter_unauthorized_user(self, mock_bot_class, mock_config):
        mock_config.TELEGRAM_TOKEN = "dummy_token"
        mock_config.CHAT_ID = "12345"

        notifier = TelegramNotifier()

        # Test authorized user
        mock_update_auth = MagicMock()
        mock_update_auth.effective_user.id = 12345

        result_auth = await notifier.filter_unauthorized_user(mock_update_auth)
        self.assertTrue(result_auth)

        # Test unauthorized user
        mock_update_unauth = MagicMock()
        mock_update_unauth.effective_user.id = 99999

        with self.assertLogs('telegram.notifier', level='WARNING') as cm:
            result_unauth = await notifier.filter_unauthorized_user(mock_update_unauth)
            self.assertFalse(result_unauth)
            self.assertTrue(any("Unauthorized access attempt from user ID: 99999" in output for output in cm.output))

if __name__ == '__main__':
    unittest.main()
