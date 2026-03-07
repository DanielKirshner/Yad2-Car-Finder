"""Custom exceptions and error codes for Yad2 Car Finder."""

from enum import IntEnum


class ErrorCode(IntEnum):
    FAILED_TO_CREATE_LOGGER_FOLDER = 1
    FAILED_TO_SETUP_LOGGER = 2
    BROWSER_START_FAILED = 3
    PAGE_LOAD_FAILED = 4
    CAPTCHA_TIMEOUT = 5
    FEED_ITEMS_NOT_FOUND = 6
    PAGINATION_PARSE_FAILED = 7
    FILE_WRITE_FAILED = 8


class CustomException(Exception):
    """Base exception for Yad2 Car Finder with an associated error code."""

    def __init__(self, message: str, error_code: ErrorCode):
        self._message = message
        self._error_code = error_code
        super().__init__(self._message)

    @property
    def error_code(self) -> ErrorCode:
        return self._error_code

    @property
    def message(self) -> str:
        return self._message

    def __str__(self) -> str:
        return f"[Error {self._error_code}] {self._message}"

    def __repr__(self) -> str:
        return f"CustomException(message='{self._message}', error_code={self._error_code})"
