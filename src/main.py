from car_search_filter import CarSearchFilter
from car_finder import Yad2CarFinder
from config import Configuration
from file_utils import FileUtils


def retrieve_results_urls(car_search_filter: CarSearchFilter) -> list[str]:
        yad2_car_finder = Yad2CarFinder()
        return list(yad2_car_finder.find(car_search_filter))


def main():
    try:
        FileUtils.dump_to_file(
             retrieve_results_urls(Configuration.CAR_SEARCH_FILTERS),
             Configuration.RESULTS_FILE_PATH)
    except KeyboardInterrupt:
        print("Stopped by user!")


if __name__ == "__main__":
    main()
