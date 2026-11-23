import asyncio
from contextlib import asynccontextmanager

import pytest

from bot import scan_scheduler
from common.exceptions import CustomException, ErrorCode

SEARCH_STEPS = ["mfr_toggle:48", "mfr_done", "mdl_toggle:10711", "mdl_done", "yr_min:2020"]


@asynccontextmanager
async def running(app):
    """The app as run_polling starts it, without polling and with jobs run by hand."""
    async with app:
        await app.post_init(app)
        try:
            yield app.bot_data["services"], app.job_queue
        finally:
            await app.job_queue.stop(wait=False)
            await app.post_shutdown(app)


async def search(telegram, app, interval: str = "10") -> None:
    await telegram.type(app, "/search")
    for step in [*SEARCH_STEPS, "yr_skip", f"interval:{interval}", "confirm_start"]:
        await telegram.tap(app, step)


async def run_scans(app) -> None:
    for job in app.job_queue.jobs():
        if job.name.startswith("scan_"):
            await job.run(app)


def _get_links(telegram) -> list[str]:
    return [line for text in telegram.texts for line in text.split("\n") if "https://" in line]


def test_search_stores_and_schedules_a_scan(make_app, telegram, yad2_search):
    async def body():
        app = make_app()
        async with running(app) as (services, _jobs):
            await search(telegram, app)

            scan = (await services.scans.list_active_in_chat(7))[0]
            assert scan.interval_minutes == 10
            assert scan.car_filter.get_url_parameters() == [
                "manufacturer=48",
                "model=10711",
                "year=2020--1",
            ]
            assert [job.data for job in app.job_queue.jobs() if job.name == "scan_1"] == [scan.id]

            await telegram.type(app, "/status")
            assert "Kia" in telegram.texts[-1]
            assert "פיקנטו" in telegram.texts[-1]
            assert "2020 - Any" in telegram.texts[-1]
            assert "0 unique cars" in telegram.texts[-1]

    asyncio.run(body())


def test_only_new_listings_are_sent(make_app, telegram, yad2_search):
    async def body():
        app = make_app()
        async with running(app):
            await search(telegram, app)
            yad2_search.list_ads("a", "b")
            await run_scans(app)
            yad2_search.list_ads("b", "c")
            await run_scans(app)
            await run_scans(app)

            assert _get_links(telegram) == ["https://yad2/a", "https://yad2/b", "https://yad2/c"]
            assert telegram.texts[-1] == "No new cars found in this scan."

    asyncio.run(body())


def test_a_restart_continues_scans_without_repeating_listings(make_app, telegram, yad2_search):
    async def body():
        app = make_app()
        async with running(app):
            await search(telegram, app)
            yad2_search.list_ads("a")
            await run_scans(app)

        app = make_app()
        async with running(app):
            yad2_search.list_ads("a", "b")
            await run_scans(app)
            await telegram.type(app, "/status")

        assert _get_links(telegram) == ["https://yad2/a", "https://yad2/b"]
        assert "2 unique cars" in telegram.texts[-1]

    asyncio.run(body())


def test_listings_of_a_failed_message_are_sent_by_the_next_scan(make_app, telegram, yad2_search):
    async def body():
        app = make_app()
        async with running(app):
            await search(telegram, app)
            yad2_search.list_ads(*(f"{i:02}" for i in range(25)))
            telegram.fails_on = lambda text: "https://yad2/10" in text
            await run_scans(app)
            assert len(_get_links(telegram)) == 10

            telegram.fails_on = lambda _text: False
            await run_scans(app)

            assert _get_links(telegram) == [f"https://yad2/{i:02}" for i in range(25)]

    asyncio.run(body())


def test_one_time_scan_ends_after_it_ran(make_app, telegram, yad2_search):
    async def body():
        app = make_app()
        async with running(app) as (services, _jobs):
            await search(telegram, app, interval="once")
            yad2_search.list_ads("a")
            await run_scans(app)

            assert _get_links(telegram) == ["https://yad2/a"]
            assert await services.scans.list_active() == []

    asyncio.run(body())


def test_a_slow_start_does_not_skip_restored_scans(make_app, telegram, yad2_search, monkeypatch):
    async def body():
        app = make_app()
        async with running(app):
            await search(telegram, app, interval="once")

        monkeypatch.setattr(scan_scheduler, "FIRST_SCAN_DELAY_IN_SECONDS", 0.05)
        yad2_search.list_ads("a")
        async with running(make_app()) as (services, _jobs):
            async with asyncio.timeout(5):
                while await services.scans.list_active():
                    await asyncio.sleep(0.02)

        assert _get_links(telegram) == ["https://yad2/a"]

    asyncio.run(body())


def test_stop_ends_the_scan(make_app, telegram, yad2_search):
    async def body():
        app = make_app()
        async with running(app) as (services, _jobs):
            await search(telegram, app)
            await telegram.type(app, "/stop")

            assert "stopped" in telegram.texts[-1]
            assert await services.scans.list_active() == []
            await telegram.type(app, "/stop")
            assert "No active scan" in telegram.texts[-1]

    asyncio.run(body())


def test_a_scan_stopped_while_it_runs_sends_nothing(make_app, telegram, yad2_search):
    async def body():
        app = make_app()
        async with running(app) as (services, _jobs):
            await search(telegram, app)
            loop = asyncio.get_running_loop()
            yad2_search.list_ads("a")
            yad2_search.on_search = lambda: asyncio.run_coroutine_threadsafe(
                services.scans.deactivate(1), loop
            ).result(timeout=5)
            await run_scans(app)

            assert _get_links(telegram) == []

    asyncio.run(body())


@pytest.mark.parametrize(
    ("error", "text"),
    [
        (
            CustomException(message="captcha", error_code=ErrorCode.CAPTCHA_TIMEOUT),
            "⚠️ Scan failed: captcha",
        ),
        (ValueError("bug"), "⚠️ Scan failed unexpectedly: bug"),
    ],
)
def test_failed_scan_is_reported_and_retried(make_app, telegram, yad2_search, error, text):
    async def body():
        app = make_app()
        async with running(app) as (services, _jobs):
            await search(telegram, app)
            yad2_search.error = error
            await run_scans(app)
            assert telegram.texts[-1] == text
            assert len(await services.scans.list_active()) == 1

    asyncio.run(body())


def test_skip_clears_models_and_years(make_app, telegram, yad2_search):
    async def body():
        app = make_app()
        async with running(app) as (services, _jobs):
            await telegram.type(app, "/search")
            for step in ["mfr_toggle:48", "mfr_done", "mdl_toggle:10711", "mdl_skip", "yr_skip"]:
                await telegram.tap(app, step)
            for step in ["interval:5", "confirm_start"]:
                await telegram.tap(app, step)

            scan = (await services.scans.list_active())[0]
            assert scan.car_filter.get_url_parameters() == ["manufacturer=48"]

    asyncio.run(body())


def test_next_without_a_manufacturer_stays_on_the_step(make_app, telegram, yad2_search):
    async def body():
        app = make_app()
        async with running(app):
            await telegram.type(app, "/search")
            await telegram.tap(app, "mfr_done")
            await telegram.tap(app, "mfr_toggle:48")

            assert telegram.texts[-1].startswith("Select manufacturer(s)")

    asyncio.run(body())
