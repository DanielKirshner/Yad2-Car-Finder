"""Entry point of the bot."""

from bot.bot import create_bot
from bot.services import BotServices
from common.config import Configuration
from common.logger import LoggerSetup, logger


def main() -> None:
    """Set up logging and run the bot until it is stopped."""
    LoggerSetup()
    logger.info("Starting Yad2 Car Finder Telegram Bot...")

    app = create_bot(BotServices.create(Configuration.Storage.DATABASE_PATH))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
