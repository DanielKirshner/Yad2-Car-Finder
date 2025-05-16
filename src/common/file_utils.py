from enum import Enum
import json


class FileMode(str, Enum):
    READ = 'r'
    WRITE = 'w'
    APPEND = 'a'


class FileUtils:
    @staticmethod
    def dump_to_file(data_to_dump: list[str], file_path: str) -> bool:
        try:
            with open(file_path, FileMode.WRITE.value) as f: # TODO: Write this content in chunks asynchronicity
                json.dump(data_to_dump, f, indent=4)
            return True
        except IOError:
            return False
