"""Parses the search results Yad2 embeds as JSON in its search pages (`__NEXT_DATA__`)."""

from dataclasses import dataclass

_ITEM_URL = "https://www.yad2.co.il/vehicles/item/{token}"


@dataclass(frozen=True)
class FeedPage:
    """One page of search results.

    Attributes:
        urls: The ads on this page
        pages: How many pages the search has
        total: How many results Yad2 reports for all pages
    """

    urls: set[str]
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
    return FeedPage(
        urls={_get_ad_url(ad) for ad in _get_ads(data)},
        pages=int(pagination.get("pages") or 0),
        total=int(pagination.get("total") or 0),
    )


def _get_ads(data: dict) -> list[dict]:
    """Return the ads of every group. Yad2 serves two layouts that group them differently."""
    groups = [group for group in data.values() if isinstance(group, list)]
    return [ad for group in groups for ad in group if isinstance(ad, dict) and ad.get("token")]


def _get_ad_url(ad: dict) -> str:
    # Receivership sales have no Yad2 page of their own, their card opens the auction site.
    return ad.get("externalKonesUrl") or _ITEM_URL.format(token=ad["token"])
