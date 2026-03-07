import os

from dotenv import load_dotenv

from .exceptions import CustomException, ErrorCode

load_dotenv()


class Configuration:
    RESULTS_FILE_NAME = "results.json"
    RESULTS_FILE_PATH = os.path.join(os.getcwd(), RESULTS_FILE_NAME)

    class Logger:
        DEFAULT_LOG_DIR_NAME: str = "logs"
        DEFAULT_LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")

    class Bot:
        TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

        @staticmethod
        def validate() -> None:
            if not Configuration.Bot.TOKEN:
                raise CustomException(
                    "TELEGRAM_BOT_TOKEN is not set in .env file",
                    ErrorCode.ENV_CONFIG_MISSING,
                )
