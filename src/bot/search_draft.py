"""The search a chat is putting together."""

from dataclasses import dataclass, field

from telegram.ext import ContextTypes

from car.car_model_catalog import CarModel
from car.car_search_filter import CarSearchFilter
from common.range import Range

_CHAT_DATA_KEY = "search_draft"
DEFAULT_INTERVAL_IN_MINUTES = 10


@dataclass
class SearchDraft:
    """Selections made so far in the search conversation.

    Attributes:
        available_models: Models offered for the selected manufacturers
        model_page: Page of the model keyboard on display
        interval_minutes: Time between scans, 0 to scan once
    """

    manufacturers: set[int] = field(default_factory=set)
    models: set[int] = field(default_factory=set)
    available_models: list[CarModel] = field(default_factory=list)
    model_page: int = 0
    year_min: int | None = None
    year_max: int | None = None
    interval_minutes: int = DEFAULT_INTERVAL_IN_MINUTES

    @property
    def selected_manufacturers(self) -> tuple[CarSearchFilter.Manufacturer, ...]:
        """The selected manufacturers, in a fixed order."""
        return tuple(CarSearchFilter.Manufacturer(value) for value in sorted(self.manufacturers))

    @property
    def model_names(self) -> tuple[str, ...]:
        """Names of the selected models."""
        return tuple(model.name for model in self.available_models if model.value in self.models)

    def offer_models(self, models: list[CarModel]) -> None:
        """Offer other models, and forget which ones were selected."""
        self.available_models = models
        self.models = set()
        self.model_page = 0

    def to_filter(self) -> CarSearchFilter:
        """Return the search filter for these selections."""
        return CarSearchFilter(
            manufacturers=self.selected_manufacturers,
            models=tuple(sorted(self.models)),
            year_range=Range(
                min=Range.INFINITE if self.year_min is None else self.year_min,
                max=Range.INFINITE if self.year_max is None else self.year_max,
            ),
        )


def start_draft(context: ContextTypes.DEFAULT_TYPE) -> SearchDraft:
    """Replace the chat's draft with an empty one."""
    context.chat_data[_CHAT_DATA_KEY] = SearchDraft()
    return context.chat_data[_CHAT_DATA_KEY]


def get_draft(context: ContextTypes.DEFAULT_TYPE) -> SearchDraft:
    """Return the chat's draft, or an empty one if it has none."""
    return context.chat_data.get(_CHAT_DATA_KEY) or start_draft(context)
