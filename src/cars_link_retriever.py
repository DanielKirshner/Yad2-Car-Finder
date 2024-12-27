from car_search_filter import CarSearchFilter
from car_finder import Yad2CarFinder

class CarsLinkRetriever:
    @staticmethod
    def retrieve_urls(car_search_filter: CarSearchFilter) -> list[str]:
        """
        Retrieves a list of car search result URLs based on the given filter.

        Args:
            car_search_filter (CarSearchFilter): The filter criteria for the search.

        Returns:
            list[str]: A list of result URLs.
        """
        yad2_car_finder = Yad2CarFinder()
        return list(yad2_car_finder.find(car_search_filter))