from common.file_utils import FileUtils
from common.config import Configuration
from common.logger import Logger
from car.cars_link_retriever import CarsLinkRetriever
import logging


def main():
    try:
        Logger()
        
        FileUtils.dump_to_file(
             CarsLinkRetriever.retrieve_urls(Configuration.CAR_SEARCH_FILTERS),
             Configuration.RESULTS_FILE_PATH)
    except KeyboardInterrupt:
        logging.warning("Stopped by user!")


if __name__ == "__main__":
    main()
