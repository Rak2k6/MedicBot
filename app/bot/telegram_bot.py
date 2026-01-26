import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes
from .handlers import setup_handlers

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.application = None

    def setup(self):
        """Set up the bot application with handlers."""
        self.application = ApplicationBuilder().token(self.token).build()
        setup_handlers(self.application)
        logger.info("Telegram bot setup complete")

    def run(self):
        """Run the bot (blocking)."""
        if self.application:
            logger.info("Starting bot polling...")
            self.application.run_polling()
        else:
            raise RuntimeError("Bot not set up. Call setup() first.")
