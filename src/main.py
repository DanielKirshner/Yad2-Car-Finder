from common.file_utils import FileUtils
from common.config import Configuration
from car.cars_link_retriever import CarsLinkRetriever


def main():
    try:
        FileUtils.dump_to_file(
             CarsLinkRetriever.retrieve_urls(Configuration.CAR_SEARCH_FILTERS),
             Configuration.RESULTS_FILE_PATH)
    except KeyboardInterrupt:
        print("Stopped by user!")


if __name__ == "__main__":
    main()
