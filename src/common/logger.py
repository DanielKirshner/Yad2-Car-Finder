import logging
import os
import sys
from datetime import datetime

from .config import Configuration
from .exceptions import CustomException, ErrorCode
from .file_utils import FileMode


class Logger:
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
                level=logging.INFO,
                filename=self._logger_file_path,
                filemode=FileMode.WRITE,
                format="%(asctime)s - %(levelname)s - %(message)s",
            )
            logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
        except Exception as e:
            raise CustomException(
                f"Failed to setup logger: {e}",
                ErrorCode.FAILED_TO_SETUP_LOGGER,
            ) from e
