"""Parses the search results Yad2 embeds as JSON in its search pages (`__NEXT_DATA__`)."""

from typing import NamedTuple

_ITEM_URL = "https://www.yad2.co.il/vehicles/item/{token}"


class FeedPage(NamedTuple):
    urls: set[str]
    pages: int
    total: int


def _get_ad_url(ad: dict) -> str:
    # Receivership sales have no Yad2 page of their own, their card opens the auction site.
    return ad.get("externalKonesUrl") or _ITEM_URL.format(token=ad["token"])


def parse_feed(queries: list[dict]) -> FeedPage | None:
    """Returns the page's results, or None if none of the page's queries holds them.

    Yad2 serves two layouts that group the ads differently, so every list of ads is read.
    """
    for query in queries:
        data = (query.get("state") or {}).get("data")
        if not isinstance(data, dict) or not isinstance(data.get("pagination"), dict):
            continue
        ads = [
            ad
            for group in data.values()
            if isinstance(group, list)
            for ad in group
            if isinstance(ad, dict) and ad.get("token")
        ]
        pagination = data["pagination"]
        return FeedPage(
            urls={_get_ad_url(ad) for ad in ads},
            pages=int(pagination.get("pages") or 0),
            total=int(pagination.get("total") or 0),
        )
    return None
