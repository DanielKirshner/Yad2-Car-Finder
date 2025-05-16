from common.file_utils import FileUtils
from common.config import Configuration
from common.logger import Logger
from car.cars_link_retriever import CarsLinkRetriever
import logging
import time


def main():
    try:
        start_time = time.time()
        
        Logger()
        
        FileUtils.dump_to_file(
             CarsLinkRetriever.retrieve_urls(Configuration.CAR_SEARCH_FILTERS),
             Configuration.RESULTS_FILE_PATH)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Execution time: {elapsed_time:.2f} seconds")
    except KeyboardInterrupt:
        logging.warning("Stopped by user!")


if __name__ == "__main__":
    main()
