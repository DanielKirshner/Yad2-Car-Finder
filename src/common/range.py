class Range:
    """Class that represents Yad2 URL ranges for parameters."""

    INFINITE: int = -1

    def __init__(self, min: int = INFINITE, max: int = INFINITE) -> None:
        self._min = min
        self._max = max

    def get_min(self) -> int:
        return self._min

    def get_max(self) -> int:
        return self._max
