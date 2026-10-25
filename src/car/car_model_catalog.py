import asyncio
import time
from typing import NamedTuple

import httpx

from car.car_search_filter import CarSearchFilter
from common.exceptions import CustomException, ErrorCode
from common.logger import logger


class CarModel(NamedTuple):
    value: int
    name: str
    manufacturer: CarSearchFilter.Manufacturer


class CarModelCatalog:
    """Fetches the models of each manufacturer from Yad2's search options API."""

    _SEARCH_OPTIONS_URL = "https://gw.yad2.co.il/search-options/vehicles/cars"
    _REQUEST_TIMEOUT_IN_SECONDS = 10
    _CACHE_TTL_IN_SECONDS = 24 * 60 * 60
    _HEADERS = {"User-Agent": "Mozilla/5.0"}

    def __init__(self) -> None:
        self._cache: dict[CarSearchFilter.Manufacturer, tuple[float, list[CarModel]]] = {}

    async def get_models(self, manufacturers: list[CarSearchFilter.Manufacturer]) -> list[CarModel]:
        """Returns the models of the given manufacturers, grouped in manufacturer order."""
        async with httpx.AsyncClient(
            headers=CarModelCatalog._HEADERS,
            timeout=CarModelCatalog._REQUEST_TIMEOUT_IN_SECONDS,
        ) as client:
            models_per_manufacturer = await asyncio.gather(
                *(self._get_manufacturer_models(client, mfr) for mfr in sorted(manufacturers))
            )
        return [model for models in models_per_manufacturer for model in models]

    async def _get_manufacturer_models(
        self, client: httpx.AsyncClient, manufacturer: CarSearchFilter.Manufacturer
    ) -> list[CarModel]:
        cached = self._cache.get(manufacturer)
        if cached and time.monotonic() - cached[0] < CarModelCatalog._CACHE_TTL_IN_SECONDS:
            return cached[1]

        models = await CarModelCatalog._fetch_manufacturer_models(client, manufacturer)
        self._cache[manufacturer] = (time.monotonic(), models)
        return models

    @staticmethod
    async def _fetch_manufacturer_models(
        client: httpx.AsyncClient, manufacturer: CarSearchFilter.Manufacturer
    ) -> list[CarModel]:
        params = {
            "fields": CarSearchFilter.UrlParameterName.MODEL,
            CarSearchFilter.UrlParameterName.MANUFACTURER: manufacturer.value,
        }
        try:
            response = await client.get(CarModelCatalog._SEARCH_OPTIONS_URL, params=params)
            response.raise_for_status()
            models = [
                CarModel(
                    value=int(option["value"]),
                    name=option["text"].strip(),
                    manufacturer=manufacturer,
                )
                for option in response.json()["data"]["model"]
            ]
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:
            logger.error(
                "Failed to fetch models", manufacturer=manufacturer.display_name, error=str(e)
            )
            raise CustomException(
                f"Failed to fetch models of {manufacturer.display_name}: {e}",
                ErrorCode.MODELS_FETCH_FAILED,
            ) from e

        logger.debug(
            "Fetched models", manufacturer=manufacturer.display_name, models_count=len(models)
        )
        return models
