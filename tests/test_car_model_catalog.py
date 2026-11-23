import asyncio
from types import SimpleNamespace

import httpx
import pytest

from car import car_model_catalog
from car.car_model_catalog import CarModelCatalog
from car.car_search_filter import CarSearchFilter
from common.exceptions import CustomException, ErrorCode

KIA = CarSearchFilter.Manufacturer.KIA
TOYOTA = CarSearchFilter.Manufacturer.TOYOTA


@pytest.fixture
def yad2(monkeypatch):
    """Serves Yad2's API from `responses` (by manufacturer id) and records the requests."""

    server = SimpleNamespace(responses={}, requests=[])

    def handle(request: httpx.Request) -> httpx.Response:
        manufacturer = request.url.params["manufacturer"]
        server.requests.append(manufacturer)
        return server.responses[manufacturer]

    real_client = httpx.AsyncClient

    def client(**kwargs):
        return real_client(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr(car_model_catalog.httpx, "AsyncClient", client)
    return server


def _options(*options: tuple[str, str]) -> httpx.Response:
    return httpx.Response(
        200, json={"data": {"model": [{"value": v, "text": t} for v, t in options]}}
    )


def test_models_are_grouped_in_manufacturer_order(yad2):
    yad2.responses = {"48": _options(("10711", "פיקנטו ")), "19": _options(("10226", "קורולה"))}

    models = asyncio.run(CarModelCatalog().get_models([KIA, TOYOTA]))

    assert [(m.value, m.name, m.manufacturer) for m in models] == [
        (10226, "קורולה", TOYOTA),
        (10711, "פיקנטו", KIA),
    ]


def test_models_are_cached(yad2):
    yad2.responses = {"48": _options(("10711", "פיקנטו"))}
    catalog = CarModelCatalog()

    asyncio.run(catalog.get_models([KIA]))
    asyncio.run(catalog.get_models([KIA]))

    assert yad2.requests == ["48"]


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503),
        httpx.Response(200, text="<html>bot check</html>"),
        httpx.Response(200, json={"data": {}}),
        httpx.Response(200, json={"data": None}),
        httpx.Response(200, json={"data": {"model": [{"value": "x", "text": "y"}]}}),
    ],
)
def test_bad_responses_raise_and_are_not_cached(yad2, response):
    yad2.responses = {"48": response}
    catalog = CarModelCatalog()

    with pytest.raises(CustomException) as error:
        asyncio.run(catalog.get_models([KIA]))
    assert error.value.error_code == ErrorCode.MODELS_FETCH_FAILED

    yad2.responses = {"48": _options(("10711", "פיקנטו"))}
    assert len(asyncio.run(catalog.get_models([KIA]))) == 1
