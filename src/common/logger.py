import json
import logging
import os
import sys
from datetime import datetime

import colorlog

from .config import Configuration
from .exceptions import CustomException, ErrorCode
from .file_utils import FileMode

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(module)s:%(funcName)s:%(lineno)d - %(message)s"
COLOR_LOG_FORMAT = (
    "%(asctime)s | %(log_color)s%(levelname)s%(reset)s | "
    "%(cyan)s%(module)s:%(funcName)s:%(lineno)d%(reset)s - %(message)s"
)
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _format_message(message: str, **kwargs: object) -> str:
    if not kwargs:
        return message
    return f"{message}\n{json.dumps(kwargs, indent=2, default=str, ensure_ascii=False)}"


class StructuredLogger:
    """Logger that accepts kwargs and formats them as JSON below the message."""

    def info(self, message: str, **kwargs: object) -> None:
        logging.info(_format_message(message, **kwargs), stacklevel=2)

    def warning(self, message: str, **kwargs: object) -> None:
        logging.warning(_format_message(message, **kwargs), stacklevel=2)

    def error(self, message: str, **kwargs: object) -> None:
        logging.error(_format_message(message, **kwargs), stacklevel=2)

    def debug(self, message: str, **kwargs: object) -> None:
        logging.debug(_format_message(message, **kwargs), stacklevel=2)


logger = StructuredLogger()


class LoggerSetup:
    def __init__(self, logger_dir_name: str = Configuration.Logger.DEFAULT_LOG_DIR_NAME) -> None:
        self._logger_dir_name = logger_dir_name
        self._logger_dir_path = os.path.join(os.getcwd(), self._logger_dir_name)
        self._logger_file_path = os.path.join(
            self._logger_dir_path,
            f"{self._get_current_timestamp()}.log",
        )
        self._setup_logger()

    def _get_current_timestamp(self) -> str:
        return str(datetime.now().strftime(r"%d-%m-%Y-%H-%M-%S"))

    def _create_logger_folder(self) -> None:
        try:
            if not os.path.exists(self._logger_dir_path):
                os.makedirs(self._logger_dir_path)
        except OSError as e:
            raise CustomException(
                f"Failed to create logger folder at '{self._logger_dir_path}': {e}",
                ErrorCode.FAILED_TO_CREATE_LOGGER_FOLDER,
            ) from e

    def _setup_logger(self) -> None:
        self._create_logger_folder()
        try:
            logging.basicConfig(
                level=getattr(logging, Configuration.Logger.DEFAULT_LOG_LEVEL, logging.DEBUG),
                filename=self._logger_file_path,
                filemode=FileMode.WRITE,
                format=LOG_FORMAT,
                datefmt=LOG_DATE_FORMAT,
            )

            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(
                colorlog.ColoredFormatter(
                    COLOR_LOG_FORMAT,
                    datefmt=LOG_DATE_FORMAT,
                    log_colors={
                        "DEBUG": "cyan",
                        "INFO": "green",
                        "WARNING": "yellow",
                        "ERROR": "red",
                        "CRITICAL": "bold_red",
                    },
                )
            )
            logging.getLogger().addHandler(console_handler)

            for lib in (
                "httpx", "httpcore", "apscheduler", "nodriver", "uc",
                "telegram", "asyncio", "websockets",
            ):
                logging.getLogger(lib).setLevel(logging.WARNING)

        except Exception as e:
            raise CustomException(
                f"Failed to setup logger: {e}",
                ErrorCode.FAILED_TO_SETUP_LOGGER,
            ) from e
