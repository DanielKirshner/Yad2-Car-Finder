"""Handlers of the bot's commands and of the search conversation."""

from typing import NamedTuple

from telegram import CallbackQuery, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes, ConversationHandler

from bot.formatting import format_search
from bot.keyboards import (
    build_confirm_keyboard,
    build_interval_keyboard,
    build_manufacturer_keyboard,
    build_model_keyboard,
    build_start_keyboard,
    build_year_max_keyboard,
    build_year_min_keyboard,
)
from bot.scan_scheduler import schedule_scan, unschedule_scan
from bot.search_draft import SearchDraft, get_draft, start_draft
from bot.services import get_services
from common.exceptions import CustomException
from common.logger import logger
from storage.models import NewScan, Scan

(
    SELECTING_MANUFACTURER,
    SELECTING_MODEL,
    SELECTING_YEAR_MIN,
    SELECTING_YEAR_MAX,
    SELECTING_INTERVAL,
    CONFIRMING,
) = range(6)


class TelegramUserInfo(NamedTuple):
    """Who triggered an update, for the logs."""

    chat_id: int
    user_id: int | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language: str | None = None

    def to_log_dict(self) -> dict:
        return {k: v for k, v in self._asdict().items() if v is not None}

    @classmethod
    def from_update(cls, update: Update) -> "TelegramUserInfo":
        user = update.effective_user
        if not user:
            return cls(chat_id=update.effective_chat.id)
        return cls(
            chat_id=update.effective_chat.id,
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language=user.language_code,
        )


def _user_context(update: Update) -> dict:
    return TelegramUserInfo.from_update(update).to_log_dict()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome the user and offer a new search."""
    logger.debug("/start command received", **_user_context(update))
    await update.message.reply_text(
        "🚗 *Yad2 Car Finder Bot*\n\n"
        "I'll help you find cars on Yad2 and notify you when new listings appear.\n\n"
        "Tap the button below to configure your search:",
        parse_mode="Markdown",
        reply_markup=build_start_keyboard(),
    )


async def search_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the search conversation, from /search or an inline button. Stops the chat's scan."""
    logger.debug("/search entry", **_user_context(update))
    await _stop_scans(context, update.effective_chat.id)
    draft = start_draft(context)

    text = "Select manufacturer(s), then tap *Next*:"
    keyboard = build_manufacturer_keyboard(draft.manufacturers)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, parse_mode="Markdown", reply_markup=keyboard
        )
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
    return SELECTING_MANUFACTURER


async def manufacturer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Toggle a manufacturer, or go on to the models."""
    query = update.callback_query
    draft = get_draft(context)

    if query.data == "mfr_done":
        return await _finish_manufacturers(update, context, draft)

    await query.answer()
    draft.manufacturers ^= {_get_callback_value(query)}
    await query.edit_message_text(
        "Select manufacturer(s), then tap *Next*:",
        parse_mode="Markdown",
        reply_markup=build_manufacturer_keyboard(draft.manufacturers),
    )
    return SELECTING_MANUFACTURER


async def _finish_manufacturers(
    update: Update, context: ContextTypes.DEFAULT_TYPE, draft: SearchDraft
) -> int:
    """Offer the models of the selected manufacturers."""
    query = update.callback_query
    if not draft.manufacturers:
        await query.answer("Please select at least one manufacturer!", show_alert=True)
        return SELECTING_MANUFACTURER

    try:
        models = await get_services(context).model_catalog.get_models(
            list(draft.selected_manufacturers)
        )
    except CustomException as err:
        logger.error("Failed to load models", **_user_context(update), error=err.message)
        await query.answer("Couldn't load models from Yad2, please try again.", show_alert=True)
        return SELECTING_MANUFACTURER

    await query.answer()
    draft.offer_models(models)
    await _show_model_keyboard(query, draft)
    return SELECTING_MODEL


async def model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Toggle a model, turn the page, or go on to the years."""
    query = update.callback_query
    draft = get_draft(context)
    await query.answer()

    if query.data in ("mdl_done", "mdl_skip"):
        return await _finish_models(query, draft)
    if query.data.startswith("mdl_toggle:"):
        draft.models ^= {_get_callback_value(query)}
        await _show_model_keyboard(query, draft)
    elif query.data.startswith("mdl_page:"):
        draft.model_page = _get_callback_value(query)
        await _show_model_keyboard(query, draft)
    return SELECTING_MODEL


async def _finish_models(query: CallbackQuery, draft: SearchDraft) -> int:
    if query.data == "mdl_skip":
        draft.models = set()
    await query.edit_message_text(
        "Select minimum year, or tap *Skip*:",
        parse_mode="Markdown",
        reply_markup=build_year_min_keyboard(),
    )
    return SELECTING_YEAR_MIN


async def _show_model_keyboard(query: CallbackQuery, draft: SearchDraft) -> None:
    text = (
        "Select model(s), or tap *Skip* / *Next*:"
        if draft.available_models
        else "No models found for the selected manufacturer(s), tap *Skip* / *Next*:"
    )
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=build_model_keyboard(draft.available_models, draft.models, draft.model_page),
    )


async def year_min_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Set the minimum year and ask for the maximum, or skip both."""
    query = update.callback_query
    await query.answer()
    if query.data == "yr_skip":
        return await _ask_interval(query)

    draft = get_draft(context)
    draft.year_min = _get_callback_value(query)
    await query.edit_message_text(
        f"Min year: *{draft.year_min}*\nSelect maximum year, or tap *Skip*:",
        parse_mode="Markdown",
        reply_markup=build_year_max_keyboard(draft.year_min),
    )
    return SELECTING_YEAR_MAX


async def year_max_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Set the maximum year, or leave it open."""
    query = update.callback_query
    await query.answer()
    if query.data != "yr_skip":
        get_draft(context).year_max = _get_callback_value(query)
    return await _ask_interval(query)


async def _ask_interval(query: CallbackQuery) -> int:
    await query.edit_message_text(
        "Select scan interval:",
        parse_mode="Markdown",
        reply_markup=build_interval_keyboard(),
    )
    return SELECTING_INTERVAL


async def interval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Set the interval and show the whole search."""
    query = update.callback_query
    await query.answer()

    draft = get_draft(context)
    draft.interval_minutes = 0 if query.data == "interval:once" else _get_callback_value(query)
    summary = format_search(draft.to_filter(), draft.model_names, draft.interval_minutes)
    await query.edit_message_text(
        f"*Search Configuration:*\n\n{summary}\n\nReady to start?",
        parse_mode="Markdown",
        reply_markup=build_confirm_keyboard(),
    )
    return CONFIRMING


async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the scan, or edit the search."""
    query = update.callback_query
    if query.data == "confirm_edit":
        return await search_entry(update, context)

    draft = get_draft(context)
    if not draft.manufacturers:
        await query.answer("No manufacturers selected! Please start over.", show_alert=True)
        logger.warning("Confirm without manufacturers", **_user_context(update))
        return CONFIRMING

    await query.answer()
    scan = await _start_scan(update, context, draft)
    await query.edit_message_text(_get_started_text(scan))
    return ConversationHandler.END


async def _start_scan(
    update: Update, context: ContextTypes.DEFAULT_TYPE, draft: SearchDraft
) -> Scan:
    """Store the draft as the chat's scan and schedule it."""
    services = get_services(context)
    user = update.effective_user
    scan = await services.scans.create(
        NewScan(
            chat_id=update.effective_chat.id,
            username=user.username if user else None,
            car_filter=draft.to_filter(),
            model_names=draft.model_names,
            interval_minutes=draft.interval_minutes,
        )
    )
    schedule_scan(context.job_queue, services.scanner, scan)
    logger.debug("Scan confirmed", **_user_context(update), scan_id=scan.id)
    return scan


def _get_started_text(scan: Scan) -> str:
    if scan.is_one_time:
        return "✅ Running a one-time scan now...\nUse /status to check results."
    return (
        f"✅ Scanning started! I'll check every {scan.interval_minutes} minutes.\n"
        f"Use /stop to stop scanning.\n"
        f"Use /status to check current configuration."
    )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stop the chat's scan."""
    stopped_count = await _stop_scans(context, update.effective_chat.id)
    logger.debug("/stop command received", **_user_context(update), stopped_count=stopped_count)
    text = (
        "⏹️ Scanning stopped. Use /search to configure a new search."
        if stopped_count
        else "ℹ️ No active scan to stop. Use /search to configure one."
    )
    await update.message.reply_text(text, reply_markup=build_start_keyboard())
    return ConversationHandler.END


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Describe the chat's scan and how much it found."""
    services = get_services(context)
    scans = await services.scans.list_active_in_chat(update.effective_chat.id)
    logger.debug("/status command received", **_user_context(update), scan_count=len(scans))

    if not scans:
        await update.message.reply_text(
            "No active scan. Use /search to configure one.",
            reply_markup=build_start_keyboard(),
        )
        return

    scan = scans[-1]
    sent_count = await services.listings.count_notified(scan.id)
    summary = format_search(scan.car_filter, scan.model_names, scan.interval_minutes)
    await update.message.reply_text(
        f"*Current Scan Status:*\n\n"
        f"🟢 Active\n"
        f"📊 {sent_count} unique cars found so far\n\n"
        f"{summary}",
        parse_mode="Markdown",
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log an error that no handler expected, and tell the user."""
    logger.error("Exception while handling an update", error=repr(context.error))
    if not isinstance(update, Update) or not update.effective_chat:
        return
    try:
        await context.bot.send_message(
            update.effective_chat.id,
            "⚠️ An error occurred. Please try again with /search.",
        )
    except TelegramError as err:
        logger.error("Failed to report an error", error=str(err))


async def _stop_scans(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> int:
    """Stop the chat's scans and return how many there were."""
    services = get_services(context)
    scans = await services.scans.list_active_in_chat(chat_id)
    for scan in scans:
        unschedule_scan(context.job_queue, scan.id)
        await services.scans.deactivate(scan.id)
    return len(scans)


def _get_callback_value(query: CallbackQuery) -> int:
    """Return the number after the colon of a button's data, such as `mdl_toggle:10711`."""
    return int(query.data.split(":")[1])
