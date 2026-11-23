"""A car ad on Yad2."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CarListing:
    """A car ad, as it appears in search results.

    Attributes:
        url: Link to the ad, unique per ad
        hand: Number of owners so far, including the current one
        price: Asking price in shekels
    """

    url: str
    manufacturer: str | None = None
    model: str | None = None
    sub_model: str | None = None
    year: int | None = None
    hand: int | None = None
    price: int | None = None
