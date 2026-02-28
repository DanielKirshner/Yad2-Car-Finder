import os

from car.car_search_filter import CarSearchFilter

from .range import Range


class Configuration:
    RESULTS_FILE_NAME = "results.json"
    RESULTS_FILE_PATH = os.path.join(os.getcwd(), RESULTS_FILE_NAME)

    CAR_SEARCH_FILTERS = CarSearchFilter(
        manufacturers=[CarSearchFilter.Manufacturer.KIA],
        models=[CarSearchFilter.Model.PICANTO],
        year_range=Range(2023, 2025),
    )

    class Logger:
        DEFAULT_LOG_DIR_NAME: str = "logs"
