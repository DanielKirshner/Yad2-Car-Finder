"""Stores the listings that scans found, and which ones were sent."""

from collections.abc import Iterable
from dataclasses import asdict

from car.car_listing import CarListing
from storage.database import Database


class ListingRepository:
    """Reads and writes listings."""

    _SAVE_STATEMENT = """
        INSERT INTO listings (url, manufacturer, model, sub_model, year, hand, price)
        VALUES (:url, :manufacturer, :model, :sub_model, :year, :hand, :price)
        ON CONFLICT (url) DO UPDATE SET
            manufacturer = excluded.manufacturer,
            model = excluded.model,
            sub_model = excluded.sub_model,
            year = excluded.year,
            hand = excluded.hand,
            price = excluded.price,
            last_seen_at = CURRENT_TIMESTAMP
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    async def save(self, listings: Iterable[CarListing]) -> None:
        """Store listings, or update the ones that are known."""
        async with self._database.transaction() as connection:
            await connection.executemany(
                self._SAVE_STATEMENT, [asdict(listing) for listing in listings]
            )

    async def get_notified_urls(self, scan_id: int) -> set[str]:
        """Return the listings a scan already sent to its chat."""
        rows = await self._database.fetch_all(
            "SELECT url FROM scan_notifications WHERE scan_id = ?", (scan_id,)
        )
        return {row["url"] for row in rows}

    async def count_notified(self, scan_id: int) -> int:
        """Return how many listings a scan sent to its chat."""
        rows = await self._database.fetch_all(
            "SELECT COUNT(*) FROM scan_notifications WHERE scan_id = ?", (scan_id,)
        )
        return rows[0][0]

    async def mark_notified(self, scan_id: int, listings: Iterable[CarListing]) -> None:
        """Remember that a scan sent these stored listings to its chat."""
        async with self._database.transaction() as connection:
            await connection.executemany(
                "INSERT OR IGNORE INTO scan_notifications (scan_id, url) VALUES (?, ?)",
                [(scan_id, listing.url) for listing in listings],
            )
