class Range:

    def __init__(self, min: int = -1, max: int = -1) -> None:
        self.__min = min
        self.__max = max
    
    def get_min(self) -> int:
        return self.__min
    
    def get_max(self) -> int:
        return self.__max
