# Yad2 Car Finder

Telegram bot that scrapes Yad2's used car listings (`nodriver`) and notifies chats about new ones.
This file is the only place for project conventions. When a change makes it or `README.md` wrong,
update them in the same change.

## Commands

```bash
pip install -r requirements.txt   # runtime dependencies
python3 src/main.py               # run the bot (needs Chrome and TELEGRAM_BOT_TOKEN in .env)
ruff check .                      # lint
ruff format --check .             # formatting
```

## Commits and pull requests

Conventional commits, as in the MacSpoofer repo:

```
<type>(<scope>): <imperative summary> (#<issue>)
```

- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`
- Scope: the area touched, e.g. `bot`, `scanner`, `scraper`, `catalog`, `docker`, `claude`
- `(#<issue>)` is the GitHub issue number. Leave it out when there is no issue
- Never add an agent as co-author
- One pull request per issue, with `Closes #<issue>` in the description
- Branches: `<type>/<issue>-<slug>`, e.g. `fix/10-filter-models-by-manufacturer`

## Structure

```
src/
  main.py                    # entry point: sets up logging, starts the bot
  bot/
    bot.py                   # Application setup, handler registration
    handlers.py              # /start, /search, /stop, /status and the search conversation
    keyboards.py             # inline keyboard builders
    scanner.py               # scan jobs, seen-URL diffing, notifications
  car/
    car_finder.py            # browser automation (nodriver)
    car_search_filter.py     # search filter parameters and enums
    car_model_catalog.py     # fetches and caches each manufacturer's models from Yad2
    cars_link_retriever.py   # runs the finder for a filter
  common/
    config.py                # configuration from .env, paths
    exceptions.py            # CustomException and ErrorCode
    logger.py                # StructuredLogger and its setup
    range.py                 # Yad2 URL ranges
```

`src` is the import root: write `from common.logger import logger`, not `from src.common...`.

## Code style

- ruff formats and lints: double quotes, spaces, 100 columns, sorted imports
- A single underscore `_` for private members (not `__`)
- Plain dash `-` in text, never an em dash

## Errors

- Raise `CustomException(message, ErrorCode.X)` with a specific code. No bare `except`, no
  booleans for failure
- Wrap third-party errors at the boundary with `raise ... from e`, and log them before raising
- Add an `ErrorCode` only when something raises it

## Async

- All I/O is async: browser, HTTP (`httpx.AsyncClient`), Telegram (`python-telegram-bot` v22+)
- `asyncio.sleep()`, never `time.sleep()`
- nodriver runs in its own event loop on a worker thread (`scanner._run_scraper_sync`) so a
  scan never blocks the bot's loop

## Logging

- `from common.logger import logger`, then `logger.info("Scan started", chat_id=1)`. Keyword
  arguments are printed as JSON under the message, so do not pass one named `message`
- In handlers, add `**_user_context(update)` so every entry says who triggered it
- `LOG_LEVEL` sets the level (default `DEBUG`). Mute noisy libraries in `LoggerSetup`

## Bot

- Search setup is a `ConversationHandler` with inline keyboards. A keyboard's callback data must
  match its pattern in `bot.py`
- Periodic scans use `JobQueue.run_repeating()`. Interval 0 is a one-time scan
- The first scan of a search sends everything it finds, later ones only what is new
- Escape anything from Yad2 with `escape_markdown` before sending it as Markdown

## Yad2

Selectors, API endpoints and how to debug scraping: the `debug-scraper` skill. Pace page loads (at
least 1 second apart): loading pages back to back triggers Yad2's bot check.
