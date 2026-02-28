from car.car_finder import Yad2CarFinder
from car.car_search_filter import CarSearchFilter


class CarsLinkRetriever:
    @staticmethod
    async def retrieve_urls(car_search_filter: CarSearchFilter) -> list[str]:
        """Retrieves a list of car search result URLs based on the given filter."""
        yad2_car_finder = Yad2CarFinder()
        return list(await yad2_car_finder.find(car_search_filter))
