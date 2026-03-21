import asyncio
from telegram import Bot
from config.settings import config
import logging

# Simple logging setup for now
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CriticalError(Exception):
    pass

class TelegramNotifier:
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.chat_id = config.CHAT_ID

        if not self.token or not self.chat_id:
            logger.critical("TELEGRAM_TOKEN or CHAT_ID is missing in environment.")
            raise CriticalError("TELEGRAM_TOKEN and CHAT_ID must be set in the environment.")

        self.bot = Bot(token=self.token)

    async def send_signal(self, symbol, direction, entry_price, stop_loss, take_profit, confidence_score):
        """
        Sends an asynchronous MarkdownV2 formatted trading signal.
        """
        direction_emoji = "🟢 LONG" if direction.upper() == "BUY" else "🔴 SHORT"

        # Escape markdown special characters
        def escape_markdown(text):
            escape_chars = r"_*[]()~`>#+-=|{}.!"
            return "".join(["\\" + char if char in escape_chars else char for char in str(text)])

        message = (
            f"*{escape_markdown(symbol)}* Sinyali\n\n"
            f"Yön: {direction_emoji}\n"
            f"Giriş Fiyatı: {escape_markdown(entry_price)}\n"
            f"Stop Loss: {escape_markdown(stop_loss)}\n"
            f"Take Profit: {escape_markdown(take_profit)}\n"
            f"Güven Skoru: {escape_markdown(confidence_score)}%\n"
        )

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="MarkdownV2"
            )
        except Exception as e:
            logger.error(f"Failed to send signal message: {e}")

    async def send_system_alert(self, message, level="INFO"):
        """
        Sends system alerts (crash, rate-limit, etc).
        """
        level_emojis = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "🚨"
        }
        emoji = level_emojis.get(level.upper(), "🔔")

        def escape_markdown(text):
            escape_chars = r"_*[]()~`>#+-=|{}.!"
            return "".join(["\\" + char if char in escape_chars else char for char in str(text)])

        formatted_message = f"{emoji} *SİSTEM BİLDİRİMİ* {emoji}\n\n{escape_markdown(message)}"

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=formatted_message,
                parse_mode="MarkdownV2"
            )
        except Exception as e:
            logger.error(f"Failed to send system alert: {e}")

    async def filter_unauthorized_user(self, update):
        """
        Silently drop messages from unauthorized users.
        """
        if str(update.effective_user.id) != str(self.chat_id):
            logger.warning(f"Unauthorized access attempt from user ID: {update.effective_user.id}")
            return False # Drop it
        return True
