from datetime import datetime
from .config import Configuration
from .file_utils import FileMode
import logging
import sys
import os


class Logger:
    def __init__(self, logger_dir_name: str = Configuration.Logger.DEFAULT_LOG_DIR_NAME) -> None:
        self.__logger_dir_name = logger_dir_name
        self.__logger_dir_path = os.path.join(
                os.getcwd(),
                self.__logger_dir_name
            )
        self.__logger_file_path = os.path.join(
                self.__logger_dir_path,
                f"{self.__get_current_timestamp()}.log"
            )
        self.__setup_logger()

    def __get_current_timestamp(self) -> str:
        return str(datetime.now().strftime(r"%d-%m-%Y-%H-%M-%S"))

    def __create_logger_folder(self) -> None:
        if not os.path.exists(self.__logger_dir_path):
            os.makedirs(self.__logger_dir_path)

    def __setup_logger(self) -> None:
        self.__create_logger_folder()

        logging.basicConfig(
                        level=logging.INFO, 
                        filename=self.__logger_file_path,
                        filemode=FileMode.WRITE,
                        format=f"%(asctime)s - %(levelname)s - %(message)s"
                    )
        logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
