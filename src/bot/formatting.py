"""Texts that describe searches."""

from telegram.helpers import escape_markdown

from car.car_search_filter import CarSearchFilter
from common.range import Range


def format_search(
    car_filter: CarSearchFilter, model_names: tuple[str, ...], interval_minutes: int
) -> str:
    """Describe a search as Markdown, one line per limit."""
    lines = []
    if car_filter.manufacturers:
        names = ", ".join(mfr.display_name for mfr in car_filter.manufacturers)
        lines.append(f"🏭 Manufacturers: {names}")
    if model_names:
        names = ", ".join(escape_markdown(name) for name in model_names)
        lines.append(f"🚙 Models: {names}")
    if car_filter.year_range.is_limited:
        lines.append(f"📅 Year: {_format_range(car_filter.year_range)}")
    lines.append(_format_interval(interval_minutes))
    return "\n".join(lines)


def _format_range(value: Range) -> str:
    low, high = (str(side) if side >= 0 else "Any" for side in (value.min, value.max))
    return f"{low} - {high}"


def _format_interval(minutes: int) -> str:
    return f"⏱️ Scan every: {minutes} minutes" if minutes > 0 else "⏱️ Scan: Once"
