from datetime import datetime

from car.car_search_filter import CarSearchFilter
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CURRENT_YEAR = datetime.now().year
MIN_YEAR = 2000


def build_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔍 New Search", callback_data="new_search")]]
    )


def build_manufacturer_keyboard(selected: set[int]) -> InlineKeyboardMarkup:
    buttons = []
    for mfr in CarSearchFilter.Manufacturer:
        prefix = "✅ " if mfr.value in selected else ""
        name = mfr.name.replace("_", " ").title()
        buttons.append(
            InlineKeyboardButton(f"{prefix}{name}", callback_data=f"mfr_toggle:{mfr.value}")
        )
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton("Next ➡️", callback_data="mfr_done")])
    return InlineKeyboardMarkup(rows)


def build_model_keyboard(selected: set[int]) -> InlineKeyboardMarkup:
    buttons = []
    for model in CarSearchFilter.Model:
        prefix = "✅ " if model.value in selected else ""
        name = model.name.replace("_", " ").title()
        buttons.append(
            InlineKeyboardButton(f"{prefix}{name}", callback_data=f"mdl_toggle:{model.value}")
        )
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
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
