from common.config import Configuration
from common.exceptions import CustomException, ErrorCode
from common.logger import logger
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
)

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


def create_bot() -> Application:
    try:
        Configuration.Bot.validate()
    except CustomException:
        raise

    try:
        app = Application.builder().token(Configuration.Bot.TOKEN).build()
    except Exception as e:
        raise CustomException(
            f"Failed to create bot application: {e}", ErrorCode.BOT_START_FAILED
        ) from e

    search_conversation = ConversationHandler(
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

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(search_conversation)
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_error_handler(error_handler)

    logger.info("Bot handlers registered successfully")
    return app
