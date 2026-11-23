"""Search parameters of Yad2's car search."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from enum import IntEnum, StrEnum

from common.range import Range

_MANUFACTURER_DISPLAY_NAME_OVERRIDES = {"BMW": "BMW", "MERCEDES_BENZ": "Mercedes-Benz"}


@dataclass(frozen=True, kw_only=True)
class CarSearchFilter:
    """What to search for. Everything that is not set is not limited."""

    class Manufacturer(IntEnum):
        AUDI = 1
        OPEL = 2
        ALFA_ROMEO = 5
        BMW = 7
        HONDA = 17
        TOYOTA = 19
        HYUNDAI = 21
        MAZDA = 27
        MITSUBISHI = 30
        MERCEDES_BENZ = 31
        NISSAN = 32
        SUBARU = 35
        SUZUKI = 36
        SEAT = 37
        CITROEN = 38
        SKODA = 40
        FIAT = 45
        KIA = 48

        @property
        def display_name(self) -> str:
            if self.name in _MANUFACTURER_DISPLAY_NAME_OVERRIDES:
                return _MANUFACTURER_DISPLAY_NAME_OVERRIDES[self.name]
            return self.name.replace("_", " ").title()

    class GearBox(IntEnum):
        MANUAL = 101
        AUTO = 102

    class Area(IntEnum):
        CENTER = 2
        SHARON = 19
        NORTH = 25
        SHFELA = 41
        SOUTH = 43
        JEHUDA = 75
        JERUSALEM = 100
        HADERA = 101

    class UrlParameterName(StrEnum):
        MANUFACTURER = "manufacturer"
        MODEL = "model"
        GEAR_BOX = "gearBox"
        YEAR = "year"
        HAND = "hand"
        KILOMETRAGE = "km"
        PRICE = "price"
        AREA = "topArea"
        PRICE_ONLY = "priceOnly"
        IMAGE_ONLY = "imgOnly"

    manufacturers: tuple[Manufacturer, ...] = ()
    models: tuple[int, ...] = ()
    gear_boxes: tuple[GearBox, ...] = ()
    year_range: Range = Range()
    hand_range: Range = Range()
    kilometrage_range: Range = Range()
    price_range: Range = Range()
    areas: tuple[Area, ...] = ()
    only_with_price: bool = False
    only_with_image: bool = False

    def get_url_parameters(self) -> list[str]:
        """Return the filter as Yad2 URL parameters, such as `year=2020--1`."""
        return [
            *self._get_selection_parameters(),
            *self._get_range_parameters(),
            *self._get_flag_parameters(),
        ]

    def _get_selection_parameters(self) -> list[str]:
        name = CarSearchFilter.UrlParameterName
        selections: list[tuple[str, Sequence[int]]] = [
            (name.MANUFACTURER, self.manufacturers),
            (name.MODEL, self.models),
            (name.GEAR_BOX, self.gear_boxes),
            (name.AREA, self.areas),
        ]
        return [
            f"{parameter}={','.join(str(int(value)) for value in values)}"
            for parameter, values in selections
            if values
        ]

    def _get_range_parameters(self) -> list[str]:
        name = CarSearchFilter.UrlParameterName
        ranges = [
            (name.YEAR, self.year_range),
            (name.HAND, self.hand_range),
            (name.KILOMETRAGE, self.kilometrage_range),
            (name.PRICE, self.price_range),
        ]
        return [f"{parameter}={value}" for parameter, value in ranges if value.is_limited]

    def _get_flag_parameters(self) -> list[str]:
        name = CarSearchFilter.UrlParameterName
        flags = [
            (name.PRICE_ONLY, self.only_with_price),
            (name.IMAGE_ONLY, self.only_with_image),
        ]
        return [f"{parameter}=1" for parameter, is_set in flags if is_set]

    def to_dict(self) -> dict:
        """Return the filter as JSON-serializable data."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CarSearchFilter:
        """Restore a filter from the data of `to_dict`."""
        return cls(
            manufacturers=tuple(cls.Manufacturer(value) for value in data["manufacturers"]),
            models=tuple(data["models"]),
            gear_boxes=tuple(cls.GearBox(value) for value in data["gear_boxes"]),
            year_range=Range(**data["year_range"]),
            hand_range=Range(**data["hand_range"]),
            kilometrage_range=Range(**data["kilometrage_range"]),
            price_range=Range(**data["price_range"]),
            areas=tuple(cls.Area(value) for value in data["areas"]),
            only_with_price=data["only_with_price"],
            only_with_image=data["only_with_image"],
        )
