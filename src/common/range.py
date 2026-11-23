"""Yad2 URL ranges."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Range:
    """A range of a search parameter. `INFINITE` leaves a side open."""

    INFINITE: ClassVar[int] = -1

    min: int = INFINITE
    max: int = INFINITE

    @property
    def is_limited(self) -> bool:
        """Whether the range excludes anything."""
        return self.min >= 0 or self.max >= 0

    def __str__(self) -> str:
        return f"{self.min}-{self.max}"
