"""Builds the Telegram application."""

from pathlib import Path
from warnings import filterwarnings

from telegram.ext import (
    AIORateLimiter,
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)
from telegram.warnings import PTBUserWarning

from bot.handlers import (
    CONFIRMING,
    SELECTING_INTERVAL,
    SELECTING_MANUFACTURER,
    SELECTING_MODEL,
    SELECTING_YEAR_MAX,
    SELECTING_YEAR_MIN,
    confirm_callback,
    error_handler,
    interval_callback,
    manufacturer_callback,
    model_callback,
    search_entry,
    start_command,
    status_command,
    stop_command,
    year_max_callback,
    year_min_callback,
)
from bot.scan_scheduler import restore_scans
from bot.services import BotServices, set_services
from common.config import Configuration
from common.exceptions import CustomException, ErrorCode
from common.logger import logger

# The search conversation starts with a command, so it cannot be tracked per message.
filterwarnings("ignore", message=".*CallbackQueryHandler", category=PTBUserWarning)

# Telegram tells how long to wait after too many messages. A first scan can send dozens.
SEND_RETRIES = 3


def create_bot(services: BotServices) -> Application:
    """Build the application, with its handlers and jobs.

    Args:
        services: Objects the handlers work with

    Raises:
        CustomException: If the configuration is incomplete or the application cannot be built
    """
    Configuration.Bot.validate()
    app = _build_application(services)
    _add_handlers(app)
    logger.info("Bot handlers registered successfully")
    return app


def _build_application(services: BotServices) -> Application:
    async def start_up(app: Application) -> None:
        await _start_up(app, services)

    async def shut_down(_app: Application) -> None:
        await services.database.close()

    try:
        app = (
            Application.builder()
            .token(Configuration.Bot.TOKEN)
            .rate_limiter(AIORateLimiter(max_retries=SEND_RETRIES))
            .post_init(start_up)
            .post_shutdown(shut_down)
            .build()
        )
    except Exception as err:
        raise CustomException(
            message=f"Failed to create bot application: {err}",
            error_code=ErrorCode.BOT_START_FAILED,
        ) from err
    set_services(app, services)
    return app


async def _start_up(app: Application, services: BotServices) -> None:
    """Open the database and start the jobs, including scans that were active before a restart."""
    await services.database.open()
    # The queue skips jobs that became due before it started, such as a restored one-time scan.
    await app.job_queue.start()
    _add_heartbeat(app)
    scans = await services.scans.list_active()
    restore_scans(app.job_queue, services.scanner, scans)
    logger.info("Scans restored", count=len(scans))


def _add_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(_build_search_conversation())
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_error_handler(error_handler)


def _build_search_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("search", search_entry),
            CallbackQueryHandler(search_entry, pattern="^new_search$"),
        ],
        states={
            SELECTING_MANUFACTURER: [
                CallbackQueryHandler(manufacturer_callback, pattern=r"^mfr_"),
            ],
            SELECTING_MODEL: [
                CallbackQueryHandler(model_callback, pattern=r"^mdl_"),
            ],
            SELECTING_YEAR_MIN: [
                CallbackQueryHandler(year_min_callback, pattern=r"^yr_min:|^yr_skip$"),
            ],
            SELECTING_YEAR_MAX: [
                CallbackQueryHandler(year_max_callback, pattern=r"^yr_max:|^yr_skip$"),
            ],
            SELECTING_INTERVAL: [
                CallbackQueryHandler(interval_callback, pattern=r"^interval:"),
            ],
            CONFIRMING: [
                CallbackQueryHandler(confirm_callback, pattern=r"^confirm_"),
            ],
        },
        fallbacks=[CommandHandler("stop", stop_command)],
        per_message=False,
    )


def _add_heartbeat(app: Application) -> None:
    if not Configuration.Bot.HEARTBEAT_FILE:
        return
    app.job_queue.run_repeating(
        _heartbeat,
        interval=Configuration.Bot.HEARTBEAT_INTERVAL_IN_SECONDS,
        first=1,  # 0 would already be in the past, and wait for a whole interval
    )


async def _heartbeat(_context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tell the container's health check that the event loop is running."""
    Path(Configuration.Bot.HEARTBEAT_FILE).touch()
