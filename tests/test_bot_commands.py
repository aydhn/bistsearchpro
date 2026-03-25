import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message
from telegram.ext import ContextTypes
from telegram_bot.bot_commands import TelegramBotManager
from config.settings import config
from data.db_manager import DatabaseManager

@pytest.fixture
def mock_db_manager():
    return MagicMock(spec=DatabaseManager)

@pytest.fixture
def bot_manager(mock_db_manager):
    with patch('telegram_bot.bot_commands.config') as mock_conf:
        mock_conf.TELEGRAM_TOKEN = 'fake_token'
        mock_conf.CHAT_ID = '123456789'
        with patch('telegram_bot.bot_commands.Application.builder') as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value.token.return_value.build.return_value = mock_app
            manager = TelegramBotManager(mock_db_manager)
            return manager

@pytest.fixture
def create_update():
    def _create_update(user_id):
        update = MagicMock(spec=Update)
        user = MagicMock(spec=User)
        user.id = user_id
        update.effective_user = user

        message = AsyncMock(spec=Message)
        update.message = message
        return update
    return _create_update

@pytest.mark.asyncio
async def test_check_auth_authorized(bot_manager, create_update):
    bot_manager.chat_id = '123456789'
    update = create_update('123456789')

    result = await bot_manager._check_auth(update)

    assert result is True
    update.message.reply_text.assert_not_called()

@pytest.mark.asyncio
async def test_check_auth_unauthorized(bot_manager, create_update):
    bot_manager.chat_id = '123456789'
    update = create_update('987654321')

    with patch('telegram_bot.bot_commands.logger.warning') as mock_warning:
        result = await bot_manager._check_auth(update)

        assert result is False
        mock_warning.assert_called_once_with("Unauthorized user 987654321 tried to use bot.")
        update.message.reply_text.assert_called_once_with("⛔ Yetkisiz erişim reddedildi.")

@pytest.mark.asyncio
async def test_commands_unauthorized(bot_manager, create_update):
    bot_manager.chat_id = '123456789'
    update = create_update('987654321')
    context = MagicMock()

    with patch.object(bot_manager, '_check_auth', return_value=False) as mock_check_auth:
        await bot_manager.start_command(update, context)
        mock_check_auth.assert_called_once_with(update)

        mock_check_auth.reset_mock()
        await bot_manager.status_command(update, context)
        mock_check_auth.assert_called_once_with(update)

        mock_check_auth.reset_mock()
        await bot_manager.report_command(update, context)
        mock_check_auth.assert_called_once_with(update)

        mock_check_auth.reset_mock()
        await bot_manager.analyze_command(update, context)
        mock_check_auth.assert_called_once_with(update)
