import logging

import nodriver as uc
from car.cars_link_retriever import CarsLinkRetriever
from common.config import Configuration
from common.file_utils import FileUtils
from common.logger import Logger


async def main():
    try:
        Logger()

        results = await CarsLinkRetriever.retrieve_urls(Configuration.CAR_SEARCH_FILTERS)
        await FileUtils.dump_to_file(results, Configuration.RESULTS_FILE_PATH)

    except KeyboardInterrupt:
        logging.warning("Stopped by user!")


if __name__ == "__main__":
    uc.loop().run_until_complete(main())
