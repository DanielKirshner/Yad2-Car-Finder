"""Parses the search results Yad2 embeds as JSON in its search pages (`__NEXT_DATA__`)."""

from dataclasses import dataclass

from car.car_listing import CarListing

_ITEM_URL = "https://www.yad2.co.il/vehicles/item/{token}"


@dataclass(frozen=True)
class FeedPage:
    """One page of search results.

    Attributes:
        listings: The ads on this page, without repeats
        pages: How many pages the search has
        total: How many results Yad2 reports for all pages
    """

    listings: tuple[CarListing, ...]
    pages: int
    total: int


def parse_feed(queries: list[dict]) -> FeedPage | None:
    """Read the search results from a page's embedded queries.

    Args:
        queries: The page's dehydrated queries, as Yad2 serves them

    Returns:
        The page's results, or None if none of the queries holds them
    """
    for query in queries:
        data = (query.get("state") or {}).get("data")
        if isinstance(data, dict) and isinstance(data.get("pagination"), dict):
            return _parse_feed_data(data)
    return None


def _parse_feed_data(data: dict) -> FeedPage:
    pagination = data["pagination"]
    listings = {ad["token"]: _parse_listing(ad) for ad in _get_ads(data)}
    return FeedPage(
        listings=tuple(listings.values()),
        pages=int(pagination.get("pages") or 0),
        total=int(pagination.get("total") or 0),
    )


def _get_ads(data: dict) -> list[dict]:
    """Return the ads of every group. Yad2 serves two layouts that group them differently."""
    groups = [group for group in data.values() if isinstance(group, list)]
    return [ad for group in groups for ad in group if isinstance(ad, dict) and ad.get("token")]


def _parse_listing(ad: dict) -> CarListing:
    return CarListing(
        url=_get_url(ad),
        manufacturer=_get_text(ad.get("manufacturer")),
        model=_get_text(ad.get("model")),
        sub_model=_get_text(ad.get("subModel")),
        year=_get_number((ad.get("vehicleDates") or {}).get("yearOfProduction")),
        hand=_get_number(ad.get("hand")),
        price=_get_number(ad.get("price")),
    )


def _get_url(ad: dict) -> str:
    # Receivership sales have no Yad2 page of their own, their card opens the auction site.
    return ad.get("externalKonesUrl") or _ITEM_URL.format(token=ad["token"])


def _get_text(value: object) -> str | None:
    """Return the text of one of Yad2's `{id, text}` objects."""
    text = value.get("text") if isinstance(value, dict) else None
    return text.strip() or None if isinstance(text, str) else None


def _get_number(value: object) -> int | None:
    """Return a number, or the id of one of Yad2's `{id, text}` objects."""
    if isinstance(value, dict):
        value = value.get("id")
    return value if isinstance(value, int) and value > 0 else None
