from Yad2CarFinder import Yad2CarFinder
from CarSearchFilter import CarSearchFilter
from Range import Range


yad2_car_finder = Yad2CarFinder()


if (__name__ == "__main__"):
    car_search_filter = CarSearchFilter(
        manufacturers=[CarSearchFilter.Manufacturer.KIA],
        models=[CarSearchFilter.Model.PICANTO],
        year_range=Range(2010))
    yad2_car_finder.find(car_search_filter)
