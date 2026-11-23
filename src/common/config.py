import os

from dotenv import load_dotenv

from .exceptions import CustomException, ErrorCode

load_dotenv()


class Configuration:
    class Logger:
        DEFAULT_LOG_DIR_NAME: str = "logs"
        DEFAULT_LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")

    class Browser:
        # Chrome's sandbox needs kernel features that containers do not have by default.
        SANDBOX: bool = os.getenv("CHROME_SANDBOX", "true").lower() != "false"

    class Bot:
        TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
        HEARTBEAT_FILE: str = os.getenv("HEARTBEAT_FILE", "")
        HEARTBEAT_INTERVAL_IN_SECONDS: int = 30

        @staticmethod
        def validate() -> None:
            if not Configuration.Bot.TOKEN:
                raise CustomException(
                    "TELEGRAM_BOT_TOKEN is not set in .env file",
                    ErrorCode.ENV_CONFIG_MISSING,
                )
