from enum import Enum
import json


class FileMode(str, Enum):
    READ = 'r'
    WRITE = 'w'
    APPEND = 'a'


class FileUtils:
    @staticmethod
    def dump_to_file(data_to_dump: list[str], file_path: str) -> None:
        with open(file_path, FileMode.WRITE.value) as f:
                json.dump(data_to_dump, f, indent=4)