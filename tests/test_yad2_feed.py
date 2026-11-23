from car.yad2_feed import parse_feed


def _query(key: str, data: object) -> dict:
    return {"queryKey": [key, "vehicles", "cars"], "state": {"data": data}}


def test_grouped_layout():
    feed = parse_feed(
        [
            _query(
                "feed",
                {
                    "platinum": [{"token": "promoted"}],
                    "boost": [],
                    "commercial": [{"token": "dealer"}, {"token": "promoted"}],
                    "private": [{"token": "private"}],
                    "pagination": {"pages": 2, "perPage": 40, "total": 49},
                },
            )
        ]
    )

    assert feed.urls == {
        "https://www.yad2.co.il/vehicles/item/promoted",
        "https://www.yad2.co.il/vehicles/item/dealer",
        "https://www.yad2.co.il/vehicles/item/private",
    }
    assert (feed.pages, feed.total) == (2, 49)


def test_mixed_layout_ignores_lists_that_are_not_ads():
    feed = parse_feed(
        [
            _query(
                "feed-mix",
                {
                    "ads": [{"token": "a"}, {"token": "b"}],
                    "slotTypes": ["private", "commercial"],
                    "pagination": {"pages": 1, "perPage": 40, "total": 2},
                },
            )
        ]
    )

    assert len(feed.urls) == 2


def test_receivership_sales_link_to_the_auction():
    feed = parse_feed(
        [
            _query(
                "feed",
                {
                    "commercial": [
                        {"token": "a", "externalKonesUrl": "https://konesy2.co.il/live/1"},
                        {"token": "b", "externalKonesUrl": None},
                    ],
                    "pagination": {"pages": 1, "total": 2},
                },
            )
        ]
    )

    assert feed.urls == {
        "https://konesy2.co.il/live/1",
        "https://www.yad2.co.il/vehicles/item/b",
    }


def test_search_without_results():
    feed = parse_feed([_query("feed", {"private": [], "pagination": {"pages": 0, "total": 0}})])

    assert feed == (set(), 0, 0)


def test_page_without_results_data():
    assert parse_feed([]) is None
    assert parse_feed([_query("feed-literal", {"manufacturer": [{"token": "x"}]})]) is None
    assert parse_feed([_query("feed", None), {"queryKey": ["feed"]}]) is None
