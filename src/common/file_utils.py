import json
import logging
from enum import Enum

import aiofiles

from .exceptions import CustomException, ErrorCode


class FileMode(str, Enum):
    READ = "r"
    WRITE = "w"
    APPEND = "a"


class FileUtils:
    @staticmethod
    async def dump_to_file(data_to_dump: list[str], file_path: str) -> None:
        try:
            async with aiofiles.open(file_path, FileMode.WRITE.value) as f:
                await f.write(json.dumps(data_to_dump, indent=4))
        except OSError as e:
            logging.error(f"Failed to write to file '{file_path}': {e}")
            raise CustomException(
                f"Failed to write to file '{file_path}': {e}",
                ErrorCode.FILE_WRITE_FAILED,
            ) from e
