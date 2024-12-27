from car_finder import Yad2CarFinder
from car_search_filter import CarSearchFilter
from range import Range
import json


RESULTS_FILE_NAME = "results.json"
yad2_car_finder = Yad2CarFinder()


if (__name__ == "__main__"):
    car_search_filter = CarSearchFilter(
        manufacturers=[CarSearchFilter.Manufacturer.KIA],
        models=[CarSearchFilter.Model.PICANTO],
        year_range=Range(2010))
    
    result_urls = list(yad2_car_finder.find(car_search_filter))
    
    with open(RESULTS_FILE_NAME, "w") as f:
        f.write(json.dumps(result_urls))
