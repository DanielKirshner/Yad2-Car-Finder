"""Models of the stored data."""

from dataclasses import dataclass

from car.car_search_filter import CarSearchFilter


@dataclass(frozen=True)
class NewScan:
    """A scan a chat asked for, before it is stored.

    Attributes:
        model_names: Names of the filter's models, to describe the scan without asking Yad2
        interval_minutes: Time between scans, 0 to scan once
    """

    chat_id: int
    username: str | None
    car_filter: CarSearchFilter
    model_names: tuple[str, ...]
    interval_minutes: int


@dataclass(frozen=True)
class Scan:
    """A stored scan."""

    id: int
    chat_id: int
    car_filter: CarSearchFilter
    model_names: tuple[str, ...]
    interval_minutes: int
    is_active: bool

    @property
    def is_one_time(self) -> bool:
        """Whether the scan ends after it ran once."""
        return self.interval_minutes == 0
