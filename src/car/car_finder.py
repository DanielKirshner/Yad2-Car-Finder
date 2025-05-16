import os
import time
import subprocess
import logging
from typing import Callable, Set
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import Chrome as ChromeDriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver import ChromeService
from selenium.webdriver.common.by import By
from car.car_search_filter import CarSearchFilter


class Yad2CarFinder:
    __CHROME_ARGUMENTS = [
        "--incognito",
        # "--headless",
        "--disable-gpu",
        "--window-size=1920,1080",
        "--disable-extensions",
        "--mute-audio",
        "--blink-settings=imagesEnabled=false",
        "--user-agent=\"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36\"" # TODO: Get the chrome version as a parameter
    ]
    __BASE_CAR_SEARCH_URL = "https://www.yad2.co.il/vehicles/cars"
    __FETCHING_INTERVAL_IN_SECONDS = 3

    @staticmethod
    def __execute_and_wait(action: Callable[[], (object | None)], wait_time_in_seconds: int) -> (object | None):
        try:
            return action()
        finally:
            time.sleep(wait_time_in_seconds)

    @staticmethod
    def __execute_verbosely(message: str, action: Callable[[], (object | None)]) -> (object | None):
        logging.info(message)
        result = None
        try:
            result = action()
            logging.info("SUCCESS!")
        except Exception as error:
            logging.error(f"ERROR!\n{error}")
        return result

    @staticmethod
    def __start_chrome_driver(chrome_arguments: list[str]) -> ChromeDriver:
        chrome_options = ChromeOptions()
        for chrome_argument in chrome_arguments:
            chrome_options.add_argument(chrome_argument)
        chrome_service = ChromeService()
        WINDOWS_OS_TYPE = 'nt'
        if os.name == WINDOWS_OS_TYPE:
            chrome_service.creation_flags |= subprocess.CREATE_NO_WINDOW
        # TODO: handle the trash log hiding in other platforms (mac os, linux, etc..)
        return ChromeDriver(chrome_options, chrome_service)
    
    @staticmethod
    def __get_car_search_url(base_car_search_url: str, car_search_filter: CarSearchFilter) -> str:
        car_search_url = base_car_search_url
        car_search_url_parameters = car_search_filter.get_url_parameters()
        if (len(car_search_url_parameters) > 0):
            car_search_url += f'?{"&".join(car_search_url_parameters)}'
        return car_search_url
    
    def find(self, car_search_filter: CarSearchFilter) -> Set[str]:
        with Yad2CarFinder.__start_chrome_driver(Yad2CarFinder.__CHROME_ARGUMENTS) as chrome_driver:
            logging.info("ChromeDriver has been started!")

            car_search_url = Yad2CarFinder.__get_car_search_url(Yad2CarFinder.__BASE_CAR_SEARCH_URL, car_search_filter)
            
            # Loading the initial page
            def load_initial_page():
                chrome_driver.get(car_search_url)
            
            Yad2CarFinder.__execute_and_wait(
                lambda: Yad2CarFinder.__execute_verbosely("Loading initial page...", load_initial_page),
                Yad2CarFinder.__FETCHING_INTERVAL_IN_SECONDS
            )

            # Closing the advertisement popup
            def close_advertisement_popup():
                try:
                    advertisement_popup_iframe_element = chrome_driver.find_element(By.XPATH, "//iframe[@title = 'Modal Message']")
                    chrome_driver.switch_to.frame(advertisement_popup_iframe_element)
                    advertisement_popup_close_button_element = chrome_driver.find_element(By.XPATH, "//*[contains(@class, 'bz-close-btn')]")
                    advertisement_popup_close_button_element.click()
                    chrome_driver.switch_to.default_content()
                except NoSuchElementException:
                    pass

            Yad2CarFinder.__execute_verbosely("Closing advertisement popup...", close_advertisement_popup)

            pagination_navbar = chrome_driver.find_element(By.XPATH, "//nav[@data-nagish='pagination-navbar']")
            pages_list = pagination_navbar.find_element(By.TAG_NAME, 'ol')
            last_page_button = pages_list.find_elements(By.TAG_NAME, 'li')[-1]
            last_page_button_text = last_page_button.find_element(By.TAG_NAME, 'a').text
            max_pages = int(last_page_button_text)

            # Walking through the search-result pages and fetching results
            result_urls: Set[str] = set()
            
            for page_number in range(1, max_pages + 1):

                def get_page():
                    # Use '?' for first query param, '&' if params already exist
                    separator = '?' if car_search_url == Yad2CarFinder.__BASE_CAR_SEARCH_URL else '&'
                    chrome_driver.get(f"{car_search_url}{separator}page={page_number}")

                Yad2CarFinder.__execute_verbosely(f"Getting page {page_number}...", get_page)

                def fetch_results():
                    result_item_elements = chrome_driver.find_elements(By.XPATH, "//div[contains(@class, 'feed-item-base_feedItemBox')]")
                    for result_item_element in result_item_elements:
                        result_item_element_link = result_item_element.find_element(By.TAG_NAME, "a").get_attribute("href").split("?")[0]
                        result_urls.add(result_item_element_link)
                Yad2CarFinder.__execute_verbosely(f"Fetching results [page {page_number}/{max_pages}]...", fetch_results)

            logging.info("ChromeDriver has been terminated!")
            logging.info(f"Collected {len(result_urls)} results")
            return result_urls
