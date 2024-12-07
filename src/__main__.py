from Yad2CarFinder import Yad2CarFinder
from CarSearchFilter import CarSearchFilter
from Range import Range


yad2_car_finder = Yad2CarFinder()


if (__name__ == "__main__"):
    car_search_filter = CarSearchFilter()
    yad2_car_finder.find(car_search_filter)
