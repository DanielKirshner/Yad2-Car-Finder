class Range:
    """
    Class that represents "Yad-2" URL ranges for parameters
    """
    INFINITE: int = -1
    
    def __init__(self, min: int = INFINITE, max: int = INFINITE) -> None:
        self.__min = min
        self.__max = max
    
    def get_min(self) -> int:
        return self.__min
    
    def get_max(self) -> int:
        return self.__max
