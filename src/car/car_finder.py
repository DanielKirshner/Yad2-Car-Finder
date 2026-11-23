"""Collects the results of a Yad2 car search with a real browser."""

import asyncio
import json
import time
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlsplit

import nodriver as uc
from nodriver.core.connection import ProtocolException

from car.browser import open_browser
from car.car_listing import CarListing
from car.car_search_filter import CarSearchFilter
from car.yad2_feed import FeedPage, parse_feed
from common.exceptions import CustomException, ErrorCode
from common.logger import logger

YAD2_HOST = "www.yad2.co.il"
SEARCH_URL = f"https://{YAD2_HOST}/vehicles/cars"


@dataclass(frozen=True)
class PageSnapshot:
    """What a browser tab shows right now."""

    url: str = ""
    queries: list[dict] = field(default_factory=list)

    @property
    def is_yad2(self) -> bool:
        """Whether the tab is on Yad2, and not on its bot check or still blank."""
        return urlsplit(self.url).hostname == YAD2_HOST

    @property
    def page_number(self) -> int:
        """Number of the results page in the tab's URL."""
        page = parse_qs(urlsplit(self.url).query).get("page", ["1"])[0]
        return int(page) if page.isdigit() else 1


class Yad2CarFinder:
    """Finds the ads that match a search filter."""

    _PAGE_INTERVAL_IN_SECONDS = 1
    _PAGE_LOAD_TIMEOUT_IN_SECONDS = 15
    _CAPTCHA_TIMEOUT_IN_SECONDS = 120
    _POLL_INTERVAL_IN_SECONDS = 1
    _SCAN_TIMEOUT_IN_SECONDS = 15 * 60

    _SNAPSHOT_EXPRESSION = """(() => {
        const element = document.getElementById("__NEXT_DATA__");
        const data = element ? JSON.parse(element.textContent) : {};
        const queries = data?.props?.pageProps?.dehydratedState?.queries || [];
        return JSON.stringify({
            url: location.href,
            queries: queries.filter(query => String(query.queryKey?.[0]).startsWith("feed")),
        });
    })()"""

    async def find(self, car_search_filter: CarSearchFilter) -> list[CarListing]:
        """Collect every ad that matches the filter.

        Args:
            car_search_filter: What to search for

        Returns:
            The ads without repeats, empty if nothing matches

        Raises:
            CustomException: If the browser or a results page fails to load, or the scan hangs
        """
        search_url = self._build_search_url(car_search_filter)
        async with open_browser() as browser:
            try:
                async with asyncio.timeout(self._SCAN_TIMEOUT_IN_SECONDS):
                    listings = await self._collect_listings(browser, search_url)
            except TimeoutError as err:
                raise CustomException(
                    message=f"Scan did not finish within {self._SCAN_TIMEOUT_IN_SECONDS}s",
                    error_code=ErrorCode.SCAN_FAILED,
                ) from err

        logger.info("Scraping complete", results_collected=len(listings))
        return listings

    @staticmethod
    def _build_search_url(car_search_filter: CarSearchFilter) -> str:
        parameters = car_search_filter.get_url_parameters()
        return f"{SEARCH_URL}?{'&'.join(parameters)}" if parameters else SEARCH_URL

    @staticmethod
    def _build_page_url(search_url: str, page_number: int) -> str:
        if page_number == 1:
            return search_url
        separator = "&" if "?" in search_url else "?"
        return f"{search_url}{separator}page={page_number}"

    async def _collect_listings(self, browser: uc.Browser, search_url: str) -> list[CarListing]:
        """Collect the ads of every results page."""
        first_page = await self._load_page(browser, search_url, page_number=1)
        listings = {listing.url: listing for listing in first_page.listings}
        for page_number in range(2, first_page.pages + 1):
            page = await self._load_page(browser, search_url, page_number)
            listings |= {listing.url: listing for listing in page.listings}

        if len(listings) < first_page.total:
            logger.warning(
                "Collected fewer results than Yad2 reports",
                collected=len(listings),
                reported=first_page.total,
            )
        return list(listings.values())

    async def _load_page(self, browser: uc.Browser, search_url: str, page_number: int) -> FeedPage:
        url = self._build_page_url(search_url, page_number)
        logger.info("Loading page", page=page_number, url=url)
        tab = await browser.get(url)
        await asyncio.sleep(self._PAGE_INTERVAL_IN_SECONDS)

        feed = await self._wait_for_feed(tab, page_number)
        logger.info("Page scraped", page=f"{page_number}/{feed.pages}", results=len(feed.listings))
        return feed

    async def _wait_for_feed(self, tab: uc.Tab, page_number: int) -> FeedPage:
        """Wait for the page's results, with extra time to solve a captcha manually."""
        feed = await self._poll_feed(tab, page_number, self._PAGE_LOAD_TIMEOUT_IN_SECONDS)
        if feed is None:
            logger.warning("Results did not load, possible CAPTCHA", page=page_number)
            feed = await self._poll_feed(tab, page_number, self._CAPTCHA_TIMEOUT_IN_SECONDS)
        if feed is None:
            raise self._get_load_error(await self._take_snapshot(tab))
        return feed

    async def _poll_feed(self, tab: uc.Tab, page_number: int, timeout: float) -> FeedPage | None:
        """Read the page until it has results, or return None after `timeout` seconds."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            snapshot = await self._take_snapshot(tab)
            # The tab still shows the previous page while the next one loads.
            if snapshot.is_yad2 and snapshot.page_number == page_number:
                feed = parse_feed(snapshot.queries)
                if feed is not None:
                    return feed
            await asyncio.sleep(self._POLL_INTERVAL_IN_SECONDS)
        return None

    async def _take_snapshot(self, tab: uc.Tab) -> PageSnapshot:
        """Read the tab's URL and embedded data, or an empty snapshot while it is loading."""
        try:
            return PageSnapshot(**json.loads(await tab.evaluate(self._SNAPSHOT_EXPRESSION)))
        except (ProtocolException, TypeError, ValueError):
            return PageSnapshot()

    @staticmethod
    def _get_load_error(snapshot: PageSnapshot) -> CustomException:
        if snapshot.is_yad2:
            return CustomException(
                message="Yad2's page has no results data",
                error_code=ErrorCode.FEED_ITEMS_NOT_FOUND,
            )
        return CustomException(
            message="Yad2 did not load, its captcha may need to be solved",
            error_code=ErrorCode.CAPTCHA_TIMEOUT,
        )
