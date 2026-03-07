from bot.bot import create_bot
from common.logger import LoggerSetup, logger


def main() -> None:
    LoggerSetup()
    logger.info("Starting Yad2 Car Finder Telegram Bot...")

    app = create_bot()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
