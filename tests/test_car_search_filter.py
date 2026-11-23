import json

from car.car_search_filter import CarSearchFilter
from common.range import Range


def test_empty_filter_has_no_parameters():
    assert CarSearchFilter().get_url_parameters() == []


def test_selections_are_comma_separated_ids():
    car_filter = CarSearchFilter(
        manufacturers=(CarSearchFilter.Manufacturer.KIA, CarSearchFilter.Manufacturer.TOYOTA),
        models=(10711, 10226),
        gear_boxes=(CarSearchFilter.GearBox.AUTO,),
        areas=(CarSearchFilter.Area.CENTER,),
    )

    assert car_filter.get_url_parameters() == [
        "manufacturer=48,19",
        "model=10711,10226",
        "gearBox=102",
        "topArea=2",
    ]


def test_open_ended_ranges_use_minus_one():
    car_filter = CarSearchFilter(
        year_range=Range(min=2020),
        hand_range=Range(max=2),
        kilometrage_range=Range(max=80000),
        price_range=Range(min=30000, max=60000),
    )

    assert car_filter.get_url_parameters() == [
        "year=2020--1",
        "hand=-1-2",
        "km=-1-80000",
        "price=30000-60000",
    ]


def test_flags_are_sent_only_when_set():
    car_filter = CarSearchFilter(only_with_price=True, only_with_image=True)

    assert car_filter.get_url_parameters() == ["priceOnly=1", "imgOnly=1"]


def test_manufacturer_display_names():
    names = {m.name: m.display_name for m in CarSearchFilter.Manufacturer}

    assert names["BMW"] == "BMW"
    assert names["MERCEDES_BENZ"] == "Mercedes-Benz"
    assert names["ALFA_ROMEO"] == "Alfa Romeo"


def test_filter_survives_json():
    car_filter = CarSearchFilter(
        manufacturers=(CarSearchFilter.Manufacturer.KIA,),
        models=(10711,),
        gear_boxes=(CarSearchFilter.GearBox.AUTO,),
        year_range=Range(min=2020),
        price_range=Range(max=60000),
        areas=(CarSearchFilter.Area.SHARON,),
        only_with_price=True,
    )

    restored = CarSearchFilter.from_dict(json.loads(json.dumps(car_filter.to_dict())))

    assert restored == car_filter
    assert restored.get_url_parameters() == car_filter.get_url_parameters()
