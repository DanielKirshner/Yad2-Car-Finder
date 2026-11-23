import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import pytest
from telegram import Update
from telegram.ext import Application
from telegram.request import HTTPXRequest

from bot.bot import create_bot
from bot.services import BotServices
from car.car_listing import CarListing
from car.car_model_catalog import CarModel
from car.car_search_filter import CarSearchFilter
from common.config import Configuration

CHAT = {"id": 7, "type": "private"}
USER = {"id": 7, "is_bot": False, "first_name": "Tester", "username": "tester"}


@dataclass
class FakeTelegram:
    """Answers the bot's requests to Telegram, and creates a user's updates."""

    texts: list[str] = field(default_factory=list)
    fails_on: Callable[[str], bool] = lambda _text: False
    _update_id: int = 0

    def answer(self, method: str, parameters: dict) -> tuple[int, dict]:
        if method == "getMe":
            return 200, {"ok": True, "result": {**USER, "id": 1, "is_bot": True}}
        if method in ("sendMessage", "editMessageText"):
            text = parameters["text"]
            if self.fails_on(text):
                return 400, {"ok": False, "error_code": 400, "description": "Bad Request"}
            self.texts.append(text)
            return 200, {"ok": True, "result": self._message(text)}
        return 200, {"ok": True, "result": True}

    async def type(self, app: Application, command: str) -> None:
        entity = {"type": "bot_command", "offset": 0, "length": len(command)}
        await self._send(app, {"message": {**self._message(command), "entities": [entity]}})

    async def tap(self, app: Application, data: str) -> None:
        query = {"id": "1", "from": USER, "chat_instance": "1", "data": data}
        await self._send(app, {"callback_query": {**query, "message": self._message("-")}})

    async def _send(self, app: Application, content: dict) -> None:
        self._update_id += 1
        update = Update.de_json({"update_id": self._update_id, **content}, app.bot)
        await app.process_update(update)

    @staticmethod
    def _message(text: str) -> dict:
        return {
            "message_id": 1,
            "date": int(time.time()),
            "chat": CHAT,
            "from": USER,
            "text": text,
        }


@pytest.fixture
def telegram(monkeypatch) -> FakeTelegram:
    fake = FakeTelegram()

    async def do_request(_self, url, method, request_data=None, **_options):
        parameters = request_data.parameters if request_data else {}
        status, body = fake.answer(url.rsplit("/", 1)[1], parameters)
        return status, json.dumps(body).encode()

    monkeypatch.setattr(HTTPXRequest, "do_request", do_request)
    monkeypatch.setattr(Configuration.Bot, "TOKEN", "1:token")
    return fake


class FakeYad2:
    """Stands in for the browser. Serves `listings`, or raises `error`."""

    def __init__(self) -> None:
        self.listings: list[CarListing] = []
        self.error: Exception | None = None
        self.on_search: Callable[[], None] = lambda: None
        self.searches: list[CarSearchFilter] = []

    def find(self, car_filter: CarSearchFilter) -> list[CarListing]:
        self.searches.append(car_filter)
        self.on_search()
        if self.error is not None:
            raise self.error
        return self.listings

    def list_ads(self, *tokens: str) -> None:
        self.listings = [CarListing(url=f"https://yad2/{token}", price=1) for token in tokens]


@pytest.fixture
def yad2_search() -> FakeYad2:
    return FakeYad2()


@pytest.fixture
def make_app(telegram, yad2_search, tmp_path):
    """Builds the bot on the test's database. Call it again to restart the bot."""

    async def get_models(manufacturers):
        return [CarModel(10711, "פיקנטו", manufacturers[0])]

    def make() -> Application:
        services = BotServices.create(str(tmp_path / "data" / "bot.sqlite3"), yad2_search.find)
        services.model_catalog.get_models = get_models
        return create_bot(services)

    return make
