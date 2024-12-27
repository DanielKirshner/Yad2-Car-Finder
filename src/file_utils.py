import json

class FileUtils:
    @staticmethod
    def dump_to_file(data_to_dump: list[str], file_path: str) -> None:
        with open(file_path, "w") as f:
                json.dump(data_to_dump, f, indent=4)