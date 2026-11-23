import asyncio
import json
import os
from types import SimpleNamespace

import pytest

from car import car_finder
from car.car_finder import Yad2CarFinder
from car.car_search_filter import CarSearchFilter
from common.exceptions import CustomException, ErrorCode

SEARCH = CarSearchFilter(manufacturers=[CarSearchFilter.Manufacturer.KIA])
SEARCH_URL = "https://www.yad2.co.il/vehicles/cars?manufacturer=48"
CAPTCHA_PAGE = json.dumps({"url": "https://validate.example.com/", "queries": []})


def _page(url: str, tokens: list[str], pages: int = 1, total: int | None = None) -> str:
    data = {
        "ads": [{"token": token} for token in tokens],
        "pagination": {"pages": pages, "total": len(tokens) if total is None else total},
    }
    return json.dumps({"url": url, "queries": [{"queryKey": ["feed"], "state": {"data": data}}]})


class FakeBrowser:
    """Serves what each URL's page evaluates to. A list is consumed, its last entry stays."""

    def __init__(self, pages: dict[str, list[str | None]]) -> None:
        self._pages = pages
        self._process = None
        self.visited: list[str] = []
        self.profile_dir: str | None = None
        self.stopped = False

    async def get(self, url: str) -> SimpleNamespace:
        self.visited.append(url)
        answers = self._pages[url]

        async def evaluate(_expression: str) -> str | None:
            return answers.pop(0) if len(answers) > 1 else answers[0]

        return SimpleNamespace(evaluate=evaluate)

    def stop(self) -> None:
        self.stopped = True


@pytest.fixture
def find(monkeypatch):
    monkeypatch.setattr(Yad2CarFinder, "_FETCHING_INTERVAL_IN_SECONDS", 0)
    monkeypatch.setattr(Yad2CarFinder, "_POLL_INTERVAL_IN_SECONDS", 0)
    monkeypatch.setattr(Yad2CarFinder, "_PAGE_LOAD_TIMEOUT_IN_SECONDS", 0.05)
    monkeypatch.setattr(Yad2CarFinder, "_CAPTCHA_TIMEOUT_IN_SECONDS", 0.05)

    def run(browser: FakeBrowser) -> set[str]:
        async def start(browser_args: list[str], user_data_dir: str) -> FakeBrowser:
            browser.profile_dir = user_data_dir
            return browser

        monkeypatch.setattr(car_finder.uc, "start", start)
        return asyncio.run(Yad2CarFinder().find(SEARCH))

    return run


def test_collects_every_page_once(find):
    browser = FakeBrowser(
        {
            SEARCH_URL: [_page(SEARCH_URL, ["a", "b"], pages=2, total=3)],
            f"{SEARCH_URL}&page=2": [_page(f"{SEARCH_URL}&page=2", ["b", "c"], pages=2, total=3)],
        }
    )

    assert {url.rsplit("/", 1)[1] for url in find(browser)} == {"a", "b", "c"}
    assert browser.visited == [SEARCH_URL, f"{SEARCH_URL}&page=2"]


def test_search_without_results_is_not_a_failure(find):
    assert find(FakeBrowser({SEARCH_URL: [_page(SEARCH_URL, [], pages=0)]})) == set()


def test_waits_for_the_page_and_a_solved_captcha(find):
    loading = [None, "not json", json.dumps({"url": SEARCH_URL, "queries": []}), CAPTCHA_PAGE]

    assert len(find(FakeBrowser({SEARCH_URL: [*loading, _page(SEARCH_URL, ["a"])]}))) == 1


def test_ignores_the_previous_page_while_the_next_one_loads(find):
    first = _page(SEARCH_URL, ["a"], pages=2, total=2)
    second = _page(f"{SEARCH_URL}&page=2", ["b"], pages=2, total=2)
    browser = FakeBrowser({SEARCH_URL: [first], f"{SEARCH_URL}&page=2": [first, second]})

    assert len(find(browser)) == 2


@pytest.mark.parametrize(
    ("page", "error_code"),
    [
        (CAPTCHA_PAGE, ErrorCode.CAPTCHA_TIMEOUT),
        (json.dumps({"url": SEARCH_URL, "queries": []}), ErrorCode.FEED_ITEMS_NOT_FOUND),
    ],
)
def test_page_that_never_loads(find, page, error_code):
    browser = FakeBrowser({SEARCH_URL: [page]})

    with pytest.raises(CustomException) as error:
        find(browser)

    assert error.value.error_code == error_code
    assert browser.stopped


def test_hung_scan_times_out_and_cleans_up(find, monkeypatch):
    monkeypatch.setattr(Yad2CarFinder, "_SCAN_TIMEOUT_IN_SECONDS", 0.05)
    browser = FakeBrowser({})

    async def hang(_url: str) -> None:
        await asyncio.Event().wait()

    browser.get = hang

    with pytest.raises(CustomException) as error:
        find(browser)

    assert error.value.error_code == ErrorCode.SCAN_FAILED
    assert browser.stopped
    assert not os.path.exists(browser.profile_dir)
