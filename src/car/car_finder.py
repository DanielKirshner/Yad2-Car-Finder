import asyncio
import json
import os
import shutil
import tempfile
import time
from urllib.parse import parse_qs, urlsplit

import nodriver as uc
from nodriver.core.connection import ProtocolException

from car.car_search_filter import CarSearchFilter
from car.yad2_feed import FeedPage, parse_feed
from common.exceptions import CustomException, ErrorCode
from common.logger import logger


class Yad2CarFinder:
    _CHROME_ARGUMENTS = [
        "--disable-gpu",
        "--window-size=1920,1080",
        "--mute-audio",
    ]  # TODO: Add headless mode
    _BASE_CAR_SEARCH_URL = "https://www.yad2.co.il/vehicles/cars"
    _HOST = "www.yad2.co.il"
    _FETCHING_INTERVAL_IN_SECONDS = 1
    _PAGE_LOAD_TIMEOUT_IN_SECONDS = 15
    _CAPTCHA_TIMEOUT_IN_SECONDS = 120
    _POLL_INTERVAL_IN_SECONDS = 1
    _SCAN_TIMEOUT_IN_SECONDS = 15 * 60
    _BROWSER_EXIT_TIMEOUT_IN_SECONDS = 10
    _PROFILE_REMOVAL_ATTEMPTS = 5

    _READ_PAGE_EXPRESSION = """(() => {
        const element = document.getElementById("__NEXT_DATA__");
        const data = element ? JSON.parse(element.textContent) : {};
        const queries = data?.props?.pageProps?.dehydratedState?.queries || [];
        return JSON.stringify({
            url: location.href,
            queries: queries.filter(query => String(query.queryKey?.[0]).startsWith("feed")),
        });
    })()"""

    @staticmethod
    async def _start_browser(chrome_arguments: list[str], profile_dir: str) -> uc.Browser:
        try:
            return await uc.start(browser_args=chrome_arguments, user_data_dir=profile_dir)
        except Exception as e:
            raise CustomException(
                f"Failed to start browser: {e}",
                ErrorCode.BROWSER_START_FAILED,
            ) from e

    @staticmethod
    async def _stop_browser(browser: uc.Browser) -> None:
        """Stop Chrome and wait for it to exit, so that its profile can be deleted."""
        process = browser._process
        browser.stop()
        if process is None:
            return
        try:
            await asyncio.wait_for(process.wait(), Yad2CarFinder._BROWSER_EXIT_TIMEOUT_IN_SECONDS)
        except TimeoutError:
            logger.warning("Browser did not exit in time, killing it")
            process.kill()
            await process.wait()

    @staticmethod
    async def _remove_profile(profile_dir: str) -> None:
        """Delete the browser's profile. Chrome's child processes may still write to it briefly."""
        for _ in range(Yad2CarFinder._PROFILE_REMOVAL_ATTEMPTS):
            await asyncio.to_thread(shutil.rmtree, profile_dir, ignore_errors=True)
            if not os.path.exists(profile_dir):
                return
            await asyncio.sleep(Yad2CarFinder._POLL_INTERVAL_IN_SECONDS)
        logger.warning("Failed to delete the browser profile", profile_dir=profile_dir)

    @staticmethod
    def _get_car_search_url(base_car_search_url: str, car_search_filter: CarSearchFilter) -> str:
        car_search_url = base_car_search_url
        car_search_url_parameters = car_search_filter.get_url_parameters()
        if len(car_search_url_parameters) > 0:
            car_search_url += f"?{'&'.join(car_search_url_parameters)}"
        return car_search_url

    @staticmethod
    def _get_page_url(car_search_url: str, page_number: int) -> str:
        if page_number == 1:
            return car_search_url
        separator = "&" if "?" in car_search_url else "?"
        return f"{car_search_url}{separator}page={page_number}"

    @staticmethod
    async def _read_page(tab: uc.Tab) -> dict:
        """Return the current URL and embedded queries, or {} while the page is loading."""
        try:
            page = json.loads(await tab.evaluate(Yad2CarFinder._READ_PAGE_EXPRESSION))
        except (ProtocolException, TypeError, ValueError):
            return {}
        return page if isinstance(page, dict) else {}

    @staticmethod
    async def _wait_for_feed(tab: uc.Tab, page_number: int) -> FeedPage:
        """Wait for the page's results, with extra time to solve a captcha manually."""
        started = time.monotonic()
        captcha_warned = False
        while True:
            page = await Yad2CarFinder._read_page(tab)
            url = urlsplit(page.get("url") or "")
            loaded_page = parse_qs(url.query).get("page", ["1"])[0]
            if url.hostname == Yad2CarFinder._HOST and loaded_page == str(page_number):
                feed = parse_feed(page["queries"])
                if feed is not None:
                    return feed

            waited = time.monotonic() - started
            if waited > Yad2CarFinder._PAGE_LOAD_TIMEOUT_IN_SECONDS and not captcha_warned:
                captcha_warned = True
                logger.warning("Results did not load, possible CAPTCHA", host=url.hostname)
            if waited > (
                Yad2CarFinder._PAGE_LOAD_TIMEOUT_IN_SECONDS
                + Yad2CarFinder._CAPTCHA_TIMEOUT_IN_SECONDS
            ):
                if url.hostname == Yad2CarFinder._HOST:
                    raise CustomException(
                        f"Yad2 page has no results data after {int(waited)}s",
                        ErrorCode.FEED_ITEMS_NOT_FOUND,
                    )
                raise CustomException(
                    f"Captcha was not solved within {int(waited)}s", ErrorCode.CAPTCHA_TIMEOUT
                )
            await asyncio.sleep(Yad2CarFinder._POLL_INTERVAL_IN_SECONDS)

    @staticmethod
    async def _load_page(browser: uc.Browser, car_search_url: str, page_number: int) -> FeedPage:
        page_url = Yad2CarFinder._get_page_url(car_search_url, page_number)
        logger.info("Loading page", page=page_number, url=page_url)
        tab = await browser.get(page_url)
        await asyncio.sleep(Yad2CarFinder._FETCHING_INTERVAL_IN_SECONDS)
        return await Yad2CarFinder._wait_for_feed(tab, page_number)

    @staticmethod
    async def _collect_urls(browser: uc.Browser, car_search_url: str) -> set[str]:
        first_page = await Yad2CarFinder._load_page(browser, car_search_url, 1)
        result_urls = set(first_page.urls)
        logger.info("Page scraped", page=f"1/{first_page.pages}", total_results=len(result_urls))

        for page_number in range(2, first_page.pages + 1):
            page = await Yad2CarFinder._load_page(browser, car_search_url, page_number)
            result_urls |= page.urls
            logger.info(
                "Page scraped",
                page=f"{page_number}/{first_page.pages}",
                total_results=len(result_urls),
            )

        if len(result_urls) < first_page.total:
            logger.warning(
                "Collected fewer results than Yad2 reports",
                collected=len(result_urls),
                reported=first_page.total,
            )
        return result_urls

    async def find(self, car_search_filter: CarSearchFilter) -> set[str]:
        car_search_url = Yad2CarFinder._get_car_search_url(
            Yad2CarFinder._BASE_CAR_SEARCH_URL, car_search_filter
        )
        profile_dir = tempfile.mkdtemp(prefix="yad2-chrome-")
        try:
            browser = await Yad2CarFinder._start_browser(
                Yad2CarFinder._CHROME_ARGUMENTS, profile_dir
            )
            try:
                logger.info("Browser started")
                async with asyncio.timeout(Yad2CarFinder._SCAN_TIMEOUT_IN_SECONDS):
                    result_urls = await Yad2CarFinder._collect_urls(browser, car_search_url)
            except TimeoutError as e:
                raise CustomException(
                    f"Scan did not finish within {Yad2CarFinder._SCAN_TIMEOUT_IN_SECONDS}s",
                    ErrorCode.SCAN_FAILED,
                ) from e
            finally:
                await Yad2CarFinder._stop_browser(browser)
        finally:
            await Yad2CarFinder._remove_profile(profile_dir)

        logger.info("Scraping complete", results_collected=len(result_urls))
        return result_urls
