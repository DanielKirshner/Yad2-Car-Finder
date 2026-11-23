"""Stores the scans of every chat."""

import json

import aiosqlite

from car.car_search_filter import CarSearchFilter
from storage.database import Database
from storage.models import NewScan, Scan


class ScanRepository:
    """Reads and writes scans."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def create(self, new_scan: NewScan) -> Scan:
        """Store a new active scan, and its chat if it is new."""
        async with self._database.transaction() as connection:
            await connection.execute(
                "INSERT INTO chats (chat_id, username) VALUES (?, ?) "
                "ON CONFLICT (chat_id) DO UPDATE SET username = excluded.username",
                (new_scan.chat_id, new_scan.username),
            )
            cursor = await connection.execute(
                "INSERT INTO scans (chat_id, car_filter, model_names, interval_minutes) "
                "VALUES (?, ?, ?, ?)",
                (
                    new_scan.chat_id,
                    json.dumps(new_scan.car_filter.to_dict()),
                    json.dumps(new_scan.model_names, ensure_ascii=False),
                    new_scan.interval_minutes,
                ),
            )
        return Scan(
            id=cursor.lastrowid,
            chat_id=new_scan.chat_id,
            car_filter=new_scan.car_filter,
            model_names=new_scan.model_names,
            interval_minutes=new_scan.interval_minutes,
            is_active=True,
        )

    async def get(self, scan_id: int) -> Scan | None:
        """Return a scan, or None if it does not exist."""
        rows = await self._database.fetch_all("SELECT * FROM scans WHERE id = ?", (scan_id,))
        return _to_scan(rows[0]) if rows else None

    async def list_active(self) -> list[Scan]:
        """Return the active scans of every chat, oldest first."""
        rows = await self._database.fetch_all("SELECT * FROM scans WHERE is_active = 1 ORDER BY id")
        return [_to_scan(row) for row in rows]

    async def list_active_in_chat(self, chat_id: int) -> list[Scan]:
        """Return a chat's active scans, oldest first."""
        rows = await self._database.fetch_all(
            "SELECT * FROM scans WHERE is_active = 1 AND chat_id = ? ORDER BY id", (chat_id,)
        )
        return [_to_scan(row) for row in rows]

    async def deactivate(self, scan_id: int) -> None:
        """Mark a scan as stopped. What it found is kept."""
        async with self._database.transaction() as connection:
            await connection.execute("UPDATE scans SET is_active = 0 WHERE id = ?", (scan_id,))


def _to_scan(row: aiosqlite.Row) -> Scan:
    return Scan(
        id=row["id"],
        chat_id=row["chat_id"],
        car_filter=CarSearchFilter.from_dict(json.loads(row["car_filter"])),
        model_names=tuple(json.loads(row["model_names"])),
        interval_minutes=row["interval_minutes"],
        is_active=bool(row["is_active"]),
    )
