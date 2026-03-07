import asyncio

from car.car_search_filter import CarSearchFilter
from car.cars_link_retriever import CarsLinkRetriever
from common.exceptions import CustomException, ErrorCode
from common.logger import logger
from telegram.ext import ContextTypes

URLS_PER_MESSAGE = 10


def _run_scraper_sync(car_filter: CarSearchFilter) -> list[str]:
    """Run the scraper in a dedicated event loop (called from a background thread)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(CarsLinkRetriever.retrieve_urls(car_filter))
    finally:
        loop.close()


class Scanner:
    def __init__(self) -> None:
        self._seen_urls: dict[int, set[str]] = {}
        self._scan_locks: dict[int, asyncio.Lock] = {}

    def _get_lock(self, chat_id: int) -> asyncio.Lock:
        if chat_id not in self._scan_locks:
            self._scan_locks[chat_id] = asyncio.Lock()
        return self._scan_locks[chat_id]

    def clear_seen_urls(self, chat_id: int) -> None:
        self._seen_urls.pop(chat_id, None)

    def get_seen_count(self, chat_id: int) -> int:
        return len(self._seen_urls.get(chat_id, set()))

    async def scan_job(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = context.job.chat_id
        car_filter: CarSearchFilter = context.job.data
        lock = self._get_lock(chat_id)

        if lock.locked():
            logger.info("Scan already in progress, skipping", chat_id=chat_id)
            return

        async with lock:
            try:
                await self._run_scan(context, chat_id, car_filter)
            except Exception as e:
                logger.error("scan_job failed", chat_id=chat_id, error=str(e))

        is_one_time = not context.job_queue.get_jobs_by_name(f"scan_{chat_id}")
        if is_one_time:
            context.chat_data["scan_active"] = False
            logger.debug("One-time scan finished, marked inactive", chat_id=chat_id)

    async def _run_scan(
        self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, car_filter: CarSearchFilter
    ) -> None:
        try:
            logger.info("Scan started", chat_id=chat_id, filters=car_filter.get_url_parameters())
            await self._send_safe(context, chat_id, "🔍 Scanning for new cars...")
            results = await asyncio.to_thread(_run_scraper_sync, car_filter) or []
            logger.info("Scan completed", chat_id=chat_id, results_count=len(results))
        except CustomException as e:
            logger.error("Scan failed", chat_id=chat_id, error_code=e.error_code, message=e.message)
            await self._send_safe(context, chat_id, f"⚠️ Scan failed: {e.message}")
            return
        except Exception as e:
            logger.error("Unexpected scan error", chat_id=chat_id, error=str(e))
            await self._send_safe(context, chat_id, f"⚠️ Scan failed unexpectedly: {e}")
            return

        seen = self._seen_urls.get(chat_id, set())
        new_urls = set(results) - seen
        self._seen_urls[chat_id] = seen | set(results)

        if new_urls:
            logger.info(
                "New cars found",
                chat_id=chat_id,
                new_count=len(new_urls),
                total_seen=len(self._seen_urls[chat_id]),
            )
            await self._send_safe(context, chat_id, f"🚗 Found {len(new_urls)} new car(s)!")
            sorted_urls = sorted(new_urls)
            for i in range(0, len(sorted_urls), URLS_PER_MESSAGE):
                batch = sorted_urls[i : i + URLS_PER_MESSAGE]
                await self._send_safe(context, chat_id, "\n".join(batch))
        else:
            logger.info(
                "No new cars found", chat_id=chat_id, total_seen=len(self._seen_urls[chat_id])
            )
            await self._send_safe(context, chat_id, "No new cars found in this scan.")

    @staticmethod
    async def _send_safe(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str) -> None:
        try:
            await context.bot.send_message(chat_id, text)
        except Exception as e:
            logger.error("Failed to send Telegram message", chat_id=chat_id, error=str(e))
            raise CustomException(
                f"Failed to send Telegram message: {e}", ErrorCode.TELEGRAM_SEND_FAILED
            ) from e
