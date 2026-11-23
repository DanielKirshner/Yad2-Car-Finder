import pytest
from telegram import InlineKeyboardMarkup

from bot import keyboards
from car.car_model_catalog import CarModel
from car.car_search_filter import CarSearchFilter

KIA = CarSearchFilter.Manufacturer.KIA
TOYOTA = CarSearchFilter.Manufacturer.TOYOTA

TELEGRAM_MAX_BUTTONS = 100
TELEGRAM_MAX_CALLBACK_BYTES = 64


def _models(manufacturer: CarSearchFilter.Manufacturer, count: int) -> list[CarModel]:
    return [
        CarModel(value=manufacturer * 1000 + i, name=f"Model {i}", manufacturer=manufacturer)
        for i in range(count)
    ]


def _buttons(markup: InlineKeyboardMarkup) -> list:
    return [button for row in markup.inline_keyboard for button in row]


def _page_count(markup: InlineKeyboardMarkup) -> int:
    indicators = [
        b.text for b in _buttons(markup) if b.callback_data == "mdl_noop" and "/" in b.text
    ]
    return int(indicators[0].split("/")[1]) if indicators else 1


@pytest.mark.parametrize("count", [0, 1, 19, 20, 21, 46, 200])
def test_every_model_is_on_exactly_one_page(count):
    models = _models(KIA, count) + _models(TOYOTA, count)
    pages = _page_count(keyboards.build_model_keyboard(models, set()))

    shown = []
    for page in range(pages):
        for button in _buttons(keyboards.build_model_keyboard(models, set(), page)):
            if button.callback_data.startswith("mdl_toggle:"):
                shown.append(int(button.callback_data.split(":")[1]))

    assert sorted(shown) == sorted(model.value for model in models)


@pytest.mark.parametrize("count", [1, 46, 200])
def test_keyboards_fit_telegram_limits(count):
    models = _models(KIA, count) + _models(TOYOTA, count)
    markups = [
        keyboards.build_manufacturer_keyboard(set()),
        keyboards.build_year_min_keyboard(),
        keyboards.build_year_max_keyboard(2000),
        keyboards.build_interval_keyboard(),
    ]
    pages = _page_count(keyboards.build_model_keyboard(models, set()))
    markups += [keyboards.build_model_keyboard(models, set(), page) for page in range(pages)]

    for markup in markups:
        buttons = _buttons(markup)
        assert len(buttons) <= TELEGRAM_MAX_BUTTONS
        assert all(len(b.callback_data.encode()) <= TELEGRAM_MAX_CALLBACK_BYTES for b in buttons)


def test_manufacturer_headers_only_with_several_manufacturers():
    def headers(models: list[CarModel]) -> list[str]:
        markup = keyboards.build_model_keyboard(models, set())
        return [b.text for b in _buttons(markup) if b.text.startswith("🏭")]

    assert headers(_models(KIA, 3)) == []
    assert headers(_models(KIA, 3) + _models(TOYOTA, 3)) == ["🏭 Kia", "🏭 Toyota"]


def test_selected_models_are_marked():
    models = _models(KIA, 2)
    texts = [b.text for b in _buttons(keyboards.build_model_keyboard(models, {models[1].value}))]

    assert "Model 0" in texts
    assert "✅ Model 1" in texts


def test_year_max_starts_at_the_chosen_minimum():
    years = [
        int(b.callback_data.split(":")[1])
        for b in _buttons(keyboards.build_year_max_keyboard(2020))
        if b.callback_data.startswith("yr_max:")
    ]

    assert min(years) == 2020
    assert max(years) == keyboards.CURRENT_YEAR
