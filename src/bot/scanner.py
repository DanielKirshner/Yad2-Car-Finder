"""Runs scans and notifies their chats about new listings."""

import asyncio
from collections.abc import Callable
from itertools import batched

from telegram import Bot
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from car.car_finder import Yad2CarFinder
from car.car_listing import CarListing
from car.car_search_filter import CarSearchFilter
from common.exceptions import CustomException, ErrorCode
from common.logger import logger
from storage.listing_repository import ListingRepository
from storage.models import Scan
from storage.scan_repository import ScanRepository

LISTINGS_PER_MESSAGE = 10

FindListings = Callable[[CarSearchFilter], list[CarListing]]


def find_listings(car_filter: CarSearchFilter) -> list[CarListing]:
    """Search Yad2 in an event loop of its own. Blocks, so call it from a worker thread.

    asyncio.run cancels the listener tasks nodriver leaves behind before it closes the loop.
    """
    return asyncio.run(Yad2CarFinder().find(car_filter))


class Scanner:
    """Scans Yad2 and sends what is new to the chat of the scan."""

    def __init__(
        self, scans: ScanRepository, listings: ListingRepository, finder: FindListings
    ) -> None:
        """Initialize a Scanner.

        Args:
            scans: Stored scans
            listings: Stored listings, and which of them were sent
            finder: Blocking function that searches Yad2
        """
        self._scans = scans
        self._listings = listings
        self._finder = finder

    async def scan_job(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Run the scan whose id is the job's data."""
        scan = await self._scans.get(context.job.data)
        if scan is None or not scan.is_active:
            logger.info("Scan was stopped, skipping", scan_id=context.job.data)
            return
        try:
            await self._run(context.bot, scan)
        finally:
            if scan.is_one_time:
                await self._scans.deactivate(scan.id)

    async def _run(self, bot: Bot, scan: Scan) -> None:
        """Scan, and report a failure to the chat."""
        try:
            await self._scan_and_notify(bot, scan)
        except CustomException as err:
            logger.error("Scan failed", scan_id=scan.id, code=err.error_code.name, error=str(err))
            if err.error_code != ErrorCode.TELEGRAM_SEND_FAILED:
                await self._report_failure(bot, scan, f"⚠️ Scan failed: {err.message}")
        except Exception as err:
            logger.error("Unexpected scan error", scan_id=scan.id, error=repr(err))
            await self._report_failure(bot, scan, f"⚠️ Scan failed unexpectedly: {err}")

    async def _scan_and_notify(self, bot: Bot, scan: Scan) -> None:
        logger.info("Scan started", scan_id=scan.id, filters=scan.car_filter.get_url_parameters())
        await self._send(bot, scan.chat_id, "🔍 Scanning for new cars...")

        listings = await asyncio.to_thread(self._finder, scan.car_filter)
        logger.info("Scan completed", scan_id=scan.id, results_count=len(listings))
        await self._listings.save(listings)

        if not await self._is_still_active(scan):
            logger.info("Scan was stopped while it ran, not notifying", scan_id=scan.id)
            return
        await self._notify(bot, scan, await self._get_new(scan, listings))

    async def _is_still_active(self, scan: Scan) -> bool:
        current = await self._scans.get(scan.id)
        return current is not None and current.is_active

    async def _get_new(self, scan: Scan, listings: list[CarListing]) -> list[CarListing]:
        notified_urls = await self._listings.get_notified_urls(scan.id)
        return [listing for listing in listings if listing.url not in notified_urls]

    async def _notify(self, bot: Bot, scan: Scan, listings: list[CarListing]) -> None:
        """Send listings. Each one counts as sent only once its message was delivered."""
        logger.info("New cars", scan_id=scan.id, new_count=len(listings))
        if not listings:
            await self._send(bot, scan.chat_id, "No new cars found in this scan.")
            return

        await self._send(bot, scan.chat_id, f"🚗 Found {len(listings)} new car(s)!")
        for batch in batched(listings, LISTINGS_PER_MESSAGE):
            await self._send(bot, scan.chat_id, "\n".join(listing.url for listing in batch))
            await self._listings.mark_notified(scan.id, batch)

    async def _report_failure(self, bot: Bot, scan: Scan, text: str) -> None:
        try:
            await self._send(bot, scan.chat_id, text)
        except CustomException as err:
            logger.error("Failed to report a failed scan", scan_id=scan.id, error=str(err))

    @staticmethod
    async def _send(bot: Bot, chat_id: int, text: str) -> None:
        try:
            await bot.send_message(chat_id, text)
        except TelegramError as err:
            raise CustomException(
                message=f"Failed to send Telegram message: {err}",
                error_code=ErrorCode.TELEGRAM_SEND_FAILED,
            ) from err
