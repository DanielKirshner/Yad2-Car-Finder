import logging
import time

import nodriver as uc
from car.car_search_filter import CarSearchFilter
from common.exceptions import CustomException, ErrorCode


class Yad2CarFinder:
    _CHROME_ARGUMENTS = [
        "--disable-gpu",
        "--window-size=1920,1080",
        "--mute-audio",
    ]
    _BASE_CAR_SEARCH_URL = "https://www.yad2.co.il/vehicles/cars"
    _FETCHING_INTERVAL_IN_SECONDS = 1
    _PAGE_LOAD_TIMEOUT_IN_SECONDS = 15
    _CAPTCHA_TIMEOUT_IN_SECONDS = 120
    _POLL_INTERVAL_IN_SECONDS = 1

    _FEED_ITEM_SELECTOR = "a[data-nagish='feed-item-card-link']"
    _PAGINATION_SELECTOR = "nav[data-nagish='pagination-navbar']"

    @staticmethod
    async def _start_browser(chrome_arguments: list[str]) -> uc.Browser:
        try:
            return await uc.start(browser_args=chrome_arguments)
        except Exception as e:
            raise CustomException(
                f"Failed to start browser: {e}",
                ErrorCode.BROWSER_START_FAILED,
            ) from e

    @staticmethod
    def _get_car_search_url(base_car_search_url: str, car_search_filter: CarSearchFilter) -> str:
        car_search_url = base_car_search_url
        car_search_url_parameters = car_search_filter.get_url_parameters()
        if len(car_search_url_parameters) > 0:
            car_search_url += f'?{"&".join(car_search_url_parameters)}'
        return car_search_url

    @staticmethod
    async def _query_elements(tab: uc.Tab, css_selector: str) -> list:
        """Run a CSS selector query via CDP and return matching elements."""
        return await tab.query_selector_all(css_selector)

    @staticmethod
    async def _poll_for_elements(
        tab: uc.Tab, css_selector: str, timeout: int, poll_interval: float = 1
    ) -> list:
        """Poll for elements matching a CSS selector until found or timeout."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            elements = await Yad2CarFinder._query_elements(tab, css_selector)
            if elements:
                return elements
            await tab.sleep(poll_interval)
        return []

    @staticmethod
    async def _wait_for_feed_items(
        tab: uc.Tab, timeout: int, captcha_timeout: int, poll_interval: float = 1
    ) -> None:
        """Wait for feed items to appear, with a fallback for manual captcha solving."""
        elements = await Yad2CarFinder._poll_for_elements(
            tab, Yad2CarFinder._FEED_ITEM_SELECTOR, timeout, poll_interval
        )
        if elements:
            return

        logging.warning(
            f"Feed items not found within {timeout}s — you may need to solve a CAPTCHA "
            f"in the browser. Waiting up to {captcha_timeout}s..."
        )
        elements = await Yad2CarFinder._poll_for_elements(
            tab, Yad2CarFinder._FEED_ITEM_SELECTOR, captcha_timeout, poll_interval
        )
        if elements:
            logging.info("Feed items appeared after captcha was solved!")
            return

        raise CustomException(
            f"Feed items not found after {captcha_timeout}s captcha timeout",
            ErrorCode.CAPTCHA_TIMEOUT,
        )

    @staticmethod
    async def _fetch_page_results(tab: uc.Tab, result_urls: set[str]) -> None:
        base_url = "https://www.yad2.co.il/vehicles/cars/"
        feed_links = await Yad2CarFinder._query_elements(tab, Yad2CarFinder._FEED_ITEM_SELECTOR)
        for link_element in feed_links:
            href = link_element.attrs.get("href")
            if href:
                clean_href = href.split("?")[0]
                if not clean_href.startswith("http"):
                    clean_href = base_url + clean_href.lstrip("/")
                result_urls.add(clean_href)

    async def find(self, car_search_filter: CarSearchFilter) -> set[str]:
        browser = await Yad2CarFinder._start_browser(Yad2CarFinder._CHROME_ARGUMENTS)
        try:
            logging.info("Browser has been started!")

            car_search_url = Yad2CarFinder._get_car_search_url(
                Yad2CarFinder._BASE_CAR_SEARCH_URL, car_search_filter
            )

            logging.info("Loading initial page...")
            tab = await browser.get(car_search_url)
            await tab.sleep(Yad2CarFinder._FETCHING_INTERVAL_IN_SECONDS)
            logging.info("SUCCESS!")

            logging.info("Closing advertisement popup...")
            try:
                popup_iframe = await Yad2CarFinder._poll_for_elements(
                    tab, "iframe[title='Modal Message']", timeout=3
                )
                if popup_iframe:
                    close_btn = await popup_iframe[0].query_selector(".bz-close-btn")
                    if close_btn:
                        await close_btn.click()
                logging.info("SUCCESS!")
            except Exception:
                logging.info("No popup found, continuing...")

            await Yad2CarFinder._wait_for_feed_items(
                tab,
                Yad2CarFinder._PAGE_LOAD_TIMEOUT_IN_SECONDS,
                Yad2CarFinder._CAPTCHA_TIMEOUT_IN_SECONDS,
                Yad2CarFinder._POLL_INTERVAL_IN_SECONDS,
            )

            max_pages = 1
            try:
                pagination = await Yad2CarFinder._query_elements(
                    tab, f"{Yad2CarFinder._PAGINATION_SELECTOR} ol li a"
                )
                if pagination:
                    last_text = pagination[-1].text.strip()
                    if last_text.isdigit():
                        max_pages = int(last_text)
                        logging.info(f"Found {max_pages} pages of results")
            except (ValueError, Exception):
                logging.info("No pagination found, assuming single page of results")

            result_urls: set[str] = set()

            for page_number in range(1, max_pages + 1):
                if page_number > 1:
                    separator = "?" if car_search_url == Yad2CarFinder._BASE_CAR_SEARCH_URL else "&"
                    page_url = f"{car_search_url}{separator}page={page_number}"

                    logging.info(f"Getting page {page_number}...")
                    await tab.get(page_url)
                    await tab.sleep(Yad2CarFinder._FETCHING_INTERVAL_IN_SECONDS)
                    logging.info("SUCCESS!")

                    await Yad2CarFinder._wait_for_feed_items(
                        tab,
                        Yad2CarFinder._PAGE_LOAD_TIMEOUT_IN_SECONDS,
                        Yad2CarFinder._CAPTCHA_TIMEOUT_IN_SECONDS,
                        Yad2CarFinder._POLL_INTERVAL_IN_SECONDS,
                    )

                logging.info(f"Fetching results [page {page_number}/{max_pages}]...")
                await Yad2CarFinder._fetch_page_results(tab, result_urls)
                logging.info("SUCCESS!")

            logging.info("Browser has been terminated!")
            logging.info(f"Collected {len(result_urls)} results")
            return result_urls
        finally:
            browser.stop()
