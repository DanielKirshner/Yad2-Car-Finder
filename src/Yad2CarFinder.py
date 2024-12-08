import os
import time
import subprocess
from typing import Callable, List
from selenium.webdriver import Chrome as ChromeDriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver import ChromeService
from selenium.webdriver.common.by import By
from CarSearchFilter import CarSearchFilter


class Yad2CarFinder:  
    __CHROME_ARGUMENTS = [
        "--incognito",
        # "--headless",
        "--disable-gpu",
        "--window-size=1920,1080",
        "--disable-extensions",
        "--mute-audio",
        "--blink-settings=imagesEnabled=false",
        "--user-agent=\"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36\""
    ]
    __BASE_CAR_SEARCH_URL = "https://www.yad2.co.il/vehicles/cars"
    __FETCHING_INTERVAL_IN_SECONDS = 3
    __MAX_SEARCH_RESULT_PAGES_TO_FETCH = 10

    @staticmethod
    def __execute_and_wait(action: Callable[[], (object | None)], wait_time_in_seconds: int) -> (object | None):
        try:
            return action()
        finally:
            time.sleep(wait_time_in_seconds)

    @staticmethod
    def __execute_verbosely(message: str, action: Callable[[], (object | None)]) -> (object | None):
        print(message, end="")
        result = None
        try:
            result = action()
            print(" SUCCESS!")
        except:
            print(" ERROR!")
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
    
    def find(self, car_search_filter: CarSearchFilter) -> List[List[str]]:
        with Yad2CarFinder.__start_chrome_driver(Yad2CarFinder.__CHROME_ARGUMENTS) as chrome_driver:
            print("ChromeDriver has been started!")

            # Loading the initial page
            def load_initial_page():
                car_search_url = Yad2CarFinder.__get_car_search_url(Yad2CarFinder.__BASE_CAR_SEARCH_URL, car_search_filter)
                chrome_driver.get(car_search_url)
            Yad2CarFinder.__execute_and_wait(
                lambda: Yad2CarFinder.__execute_verbosely("Loading initial page...", load_initial_page),
                Yad2CarFinder.__FETCHING_INTERVAL_IN_SECONDS
            )

            # Closing the advertisement popup
            def close_advertisement_popup():
                advertisement_popup_iframe_element = chrome_driver.find_element(By.XPATH, "//iframe[@title = 'Modal Message']")
                chrome_driver.switch_to.frame(advertisement_popup_iframe_element)
                advertisement_popup_close_button_element = chrome_driver.find_element(By.XPATH, "//*[contains(@class, 'bz-close-btn')]")
                advertisement_popup_close_button_element.click()
                chrome_driver.switch_to.default_content()
            Yad2CarFinder.__execute_verbosely("Closing advertisement popup...", close_advertisement_popup)

            # Walking through the search-result pages and fetching results
            result_urls: List[List[str]] = []
            next_page_button_element = chrome_driver.find_element(By.XPATH, "(//a[contains(@class, 'pagination-arrow_button')])[2]")
            for i in range(Yad2CarFinder.__MAX_SEARCH_RESULT_PAGES_TO_FETCH):
                result_urls.append([])
                def fetch_results():
                    result_item_elements = chrome_driver.find_elements(By.XPATH, "//div[contains(@class, 'feed-item-base_feedItemBox')]")
                    for result_item_element in result_item_elements:
                        result_item_element_link = result_item_element.find_element(By.TAG_NAME, "a").get_attribute("href").split("?")[0]
                        result_urls[i].append(result_item_element_link)
                Yad2CarFinder.__execute_verbosely(f"Fetching results [page {i + 1}/{Yad2CarFinder.__MAX_SEARCH_RESULT_PAGES_TO_FETCH}]...", fetch_results)
                if (i < Yad2CarFinder.__MAX_SEARCH_RESULT_PAGES_TO_FETCH - 1):
                    def go_to_next_page():
                        chrome_driver.execute_script("arguments[0].scrollIntoView();", next_page_button_element)
                        chrome_driver.execute_script("window.scrollBy(0, -100);", next_page_button_element)
                        Yad2CarFinder.__execute_and_wait(
                            lambda: next_page_button_element.click(),
                            Yad2CarFinder.__FETCHING_INTERVAL_IN_SECONDS
                        )
                    Yad2CarFinder.__execute_verbosely(f"Going to page {i + 2}...", go_to_next_page)

            print("ChromeDriver has been terminated!")
            return result_urls
