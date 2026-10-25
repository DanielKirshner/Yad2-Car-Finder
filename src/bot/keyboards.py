from datetime import datetime
from itertools import groupby
from operator import attrgetter

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from car.car_model_catalog import CarModel
from car.car_search_filter import CarSearchFilter

CURRENT_YEAR = datetime.now().year
MIN_YEAR = 2000
MODEL_COLUMNS = 2
MODEL_ROWS_PER_PAGE = 10


def build_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔍 New Search", callback_data="new_search")]]
    )


def build_manufacturer_keyboard(selected: set[int]) -> InlineKeyboardMarkup:
    buttons = []
    for mfr in CarSearchFilter.Manufacturer:
        prefix = "✅ " if mfr.value in selected else ""
        buttons.append(
            InlineKeyboardButton(
                f"{prefix}{mfr.display_name}", callback_data=f"mfr_toggle:{mfr.value}"
            )
        )
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton("Next ➡️", callback_data="mfr_done")])
    return InlineKeyboardMarkup(rows)


def _paginate_model_rows(
    models: list[CarModel], selected: set[int]
) -> list[list[list[InlineKeyboardButton]]]:
    """Splits the model buttons into pages, heading each manufacturer's models on every page."""
    show_headers = len({model.manufacturer for model in models}) > 1
    pages: list[list[list[InlineKeyboardButton]]] = [[]]
    for manufacturer, group in groupby(models, key=attrgetter("manufacturer")):
        buttons = [
            InlineKeyboardButton(
                f"{'✅ ' if model.value in selected else ''}{model.name}",
                callback_data=f"mdl_toggle:{model.value}",
            )
            for model in group
        ]
        header = [InlineKeyboardButton(f"🏭 {manufacturer.display_name}", callback_data="mdl_noop")]
        header_on_page = False
        for i in range(0, len(buttons), MODEL_COLUMNS):
            needs_header = show_headers and not header_on_page
            if len(pages[-1]) + needs_header + 1 > MODEL_ROWS_PER_PAGE:
                pages.append([])
                needs_header = show_headers
            if needs_header:
                pages[-1].append(header)
                header_on_page = True
            pages[-1].append(buttons[i : i + MODEL_COLUMNS])
    return pages


def build_model_keyboard(
    models: list[CarModel], selected: set[int], page: int = 0
) -> InlineKeyboardMarkup:
    pages = _paginate_model_rows(models, selected)
    page %= len(pages)
    rows = list(pages[page])
    if len(pages) > 1:
        rows.append(
            [
                InlineKeyboardButton("◀️", callback_data=f"mdl_page:{(page - 1) % len(pages)}"),
                InlineKeyboardButton(f"{page + 1}/{len(pages)}", callback_data="mdl_noop"),
                InlineKeyboardButton("▶️", callback_data=f"mdl_page:{(page + 1) % len(pages)}"),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton("Skip ⏭️", callback_data="mdl_skip"),
            InlineKeyboardButton("Next ➡️", callback_data="mdl_done"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def build_year_min_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(str(year), callback_data=f"yr_min:{year}")
        for year in range(CURRENT_YEAR, MIN_YEAR - 1, -1)
    ]
    rows = [buttons[i : i + 4] for i in range(0, len(buttons), 4)]
    rows.append([InlineKeyboardButton("Skip ⏭️", callback_data="yr_skip")])
    return InlineKeyboardMarkup(rows)


def build_year_max_keyboard(min_year: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(str(year), callback_data=f"yr_max:{year}")
        for year in range(CURRENT_YEAR, min_year - 1, -1)
    ]
    rows = [buttons[i : i + 4] for i in range(0, len(buttons), 4)]
    rows.append([InlineKeyboardButton("Skip ⏭️", callback_data="yr_skip")])
    return InlineKeyboardMarkup(rows)


def build_interval_keyboard() -> InlineKeyboardMarkup:
    intervals = [5, 10, 15, 30, 60]
    buttons = [InlineKeyboardButton(f"{m} min", callback_data=f"interval:{m}") for m in intervals]
    once_button = InlineKeyboardButton("Once 🔂", callback_data="interval:once")
    return InlineKeyboardMarkup([buttons[:3], buttons[3:], [once_button]])


def build_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🚀 Start Scanning", callback_data="confirm_start"),
                InlineKeyboardButton("✏️ Edit", callback_data="confirm_edit"),
            ]
        ]
    )
