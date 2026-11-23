import asyncio
import sqlite3
import threading

import pytest

from car.car_listing import CarListing
from car.car_search_filter import CarSearchFilter
from common.exceptions import CustomException, ErrorCode
from common.range import Range
from storage.database import Database
from storage.listing_repository import ListingRepository
from storage.migrations import MIGRATIONS
from storage.models import NewScan
from storage.scan_repository import ScanRepository

KIA = CarSearchFilter(manufacturers=(CarSearchFilter.Manufacturer.KIA,), year_range=Range(min=2020))


def _new_scan(chat_id: int = 7, interval_minutes: int = 10) -> NewScan:
    return NewScan(
        chat_id=chat_id,
        username="tester",
        car_filter=KIA,
        model_names=("פיקנטו",),
        interval_minutes=interval_minutes,
    )


@pytest.fixture
def run(tmp_path):
    """Runs an async test body with an open database."""

    def runner(body):
        async def with_database():
            database = Database(str(tmp_path / "data" / "bot.sqlite3"))
            await database.open()
            try:
                return await body(database)
            finally:
                await database.close()

        return asyncio.run(with_database())

    return runner


def test_scans_survive_a_restart(run):
    created = run(lambda database: ScanRepository(database).create(_new_scan()))
    restored = run(lambda database: ScanRepository(database).list_active())

    assert restored == [created]
    assert restored[0].car_filter == KIA
    assert restored[0].model_names == ("פיקנטו",)


def test_stopped_scans_are_not_active(run):
    async def body(database):
        scans = ScanRepository(database)
        first, second = await scans.create(_new_scan()), await scans.create(_new_scan())
        other_chat = await scans.create(_new_scan(chat_id=8))
        await scans.deactivate(first.id)

        assert await scans.list_active_in_chat(7) == [second]
        assert await scans.list_active() == [second, other_chat]
        assert not (await scans.get(first.id)).is_active
        assert await scans.get(999) is None

    run(body)


def test_notified_listings_are_per_scan(run):
    async def body(database):
        scans, listings = ScanRepository(database), ListingRepository(database)
        first, second = await scans.create(_new_scan()), await scans.create(_new_scan())
        car = CarListing(url="https://yad2/a", price=50000)
        await listings.save([car])
        await listings.mark_notified(first.id, [car])
        await listings.mark_notified(first.id, [car])

        assert await listings.get_notified_urls(first.id) == {"https://yad2/a"}
        assert await listings.count_notified(first.id) == 1
        assert await listings.get_notified_urls(second.id) == set()

    run(body)


def test_saving_a_known_listing_updates_it(run):
    async def body(database):
        listings = ListingRepository(database)
        await listings.save([CarListing(url="https://yad2/a", price=50000)])
        await listings.save([CarListing(url="https://yad2/a", price=45000)])

        rows = await database.fetch_all("SELECT url, price FROM listings")
        assert [tuple(row) for row in rows] == [("https://yad2/a", 45000)]

    run(body)


def test_a_failed_transaction_changes_nothing(run):
    async def body(database):
        with pytest.raises(CustomException) as error:
            async with database.transaction() as connection:
                await connection.execute("INSERT INTO chats (chat_id) VALUES (1)")
                await connection.execute("INSERT INTO missing VALUES (1)")

        assert error.value.error_code == ErrorCode.STORAGE_FAILED
        assert await database.fetch_all("SELECT * FROM chats") == []
        async with database.transaction() as connection:
            await connection.execute("INSERT INTO chats (chat_id) VALUES (2)")

    run(body)


def test_parallel_transactions_do_not_mix(run):
    async def body(database):
        scans = ScanRepository(database)
        created = await asyncio.gather(*(scans.create(_new_scan(chat_id=i)) for i in range(20)))

        assert len({scan.id for scan in created}) == 20
        assert [scan.chat_id for scan in await scans.list_active()] == list(range(20))

    run(body)


def test_migrations_run_once(run, tmp_path):
    async def version(database):
        return (await database.fetch_all("PRAGMA user_version"))[0][0]

    assert run(version) == len(MIGRATIONS)
    assert run(version) == len(MIGRATIONS)


def test_unusable_database_is_a_clear_error(tmp_path):
    path = tmp_path / "bot.sqlite3"
    threads_before = threading.active_count()
    path.write_text("not a database, but long enough to be read as one" * 100)

    with pytest.raises(CustomException) as error:
        asyncio.run(Database(str(path)).open())

    assert error.value.error_code == ErrorCode.STORAGE_FAILED
    assert threading.active_count() == threads_before, "the process would never exit"


def test_schema_enforces_references(run, tmp_path):
    async def body(database):
        with pytest.raises(CustomException) as error:
            await ListingRepository(database).mark_notified(1, [CarListing(url="https://yad2/a")])
        assert isinstance(error.value.__cause__, sqlite3.IntegrityError)

    run(body)
