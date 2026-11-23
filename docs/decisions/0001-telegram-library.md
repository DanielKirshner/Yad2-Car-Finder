# 0001 - Telegram library

## Status

Proposed, 2026-11-23. Accepted when merged. Answers [#19](https://github.com/DanielKirshner/Yad2-Car-Finder/issues/19).

## Context

The bot runs on python-telegram-bot (PTB) 22.6. #19 asks whether Telethon would serve it better, and says to migrate only for a tangible gain in performance, features or code simplicity.

What `src/bot/` and `src/main.py` use on master (f25534e):

- One six-state `ConversationHandler`, driven by `CallbackQueryHandler` regex patterns.
- Inline keyboards, message edits, callback answers and alert popups.
- `JobQueue.run_once`, `run_repeating` and `get_jobs_by_name`, at intervals of 5 to 60 minutes.
- `context.chat_data`, in memory only. The app configures no persistence.
- Text messages. It sends no photos or files.
- One token from `.env`, long polling, one global error handler.

Async is not a difference. PTB is [a pure Python, asynchronous interface](https://github.com/python-telegram-bot/python-telegram-bot#introduction). The extra event loop in `scanner.py` exists for nodriver and would stay under either library.

## Options

1. Stay on PTB.
2. Move to Telethon v1 (1.46.0, the version on [PyPI](https://pypi.org/project/Telethon/)).
3. Move to Telethon v2. Rejected outright: its docs are labelled [2.0.0a0](https://docs.telethon.dev/en/v2/), PyPI has [no 2.x release](https://pypi.org/pypi/Telethon/json), and it [removes `client.conversation()`](https://docs.telethon.dev/en/v2/developing/migration-guide.html) and tells you to write your own state machine.

## Comparison

| Point | PTB | Telethon v1 |
|---|---|---|
| Performance | HTTPS to the Bot API, long polling | [Direct MTProto connection](https://docs.telethon.dev/en/stable/concepts/botapi-vs-mtproto.html), one hop fewer. Not measured, see below |
| Inline keyboards | Yes, in use today | Yes, with [`Button.inline`](https://docs.telethon.dev/en/stable/modules/custom.html) and [`events.CallbackQuery`](https://docs.telethon.dev/en/stable/modules/events.html), including alerts and a 64-byte data limit |
| Conversations | [`ConversationHandler`](https://docs.python-telegram-bot.org/en/stable/telegram.ext.conversationhandler.html) | [`client.conversation()`](https://docs.telethon.dev/en/stable/modules/client.html) exists, but its own docs list "lacking persistence, poor interaction with other event handlers" and point bot authors to a hand-written state machine |
| Scheduling | [`JobQueue`](https://docs.python-telegram-bot.org/en/stable/telegram.ext.jobqueue.html) on APScheduler | None, ["unnecessary bloat"](https://codeberg.org/Lonami/Telethon/wiki/Scheduling-Functions). Use asyncio or APScheduler directly |
| Update order | [One by one](https://docs.python-telegram-bot.org/en/stable/telegram.ext.applicationbuilder.html) by default, which a conversation needs | Concurrent by default. Needs [`sequential_updates=True`](https://docs.telethon.dev/en/stable/modules/client.html) |
| Error handler | [`add_error_handler`](https://docs.python-telegram-bot.org/en/stable/telegram.ext.application.html) | None. [Handler exceptions are only logged](https://codeberg.org/Lonami/Telethon/src/branch/v1/telethon/client/updates.py), so each handler needs a wrapper |
| Formatted text | [Markdown and HTML](https://docs.python-telegram-bot.org/en/stable/telegram.bot.html), off by default | [Markdown and HTML](https://codeberg.org/Lonami/Telethon/src/branch/v1/telethon/client/messageparse.py), Markdown on by default |
| Media | [`send_photo`](https://docs.python-telegram-bot.org/en/stable/telegram.bot.html) and similar, by file, URL or file_id | [`send_file`](https://docs.telethon.dev/en/stable/modules/client.html) for all types, by file, URL or file_id |
| File limits | [50 MB up, 20 MB down](https://core.telegram.org/bots/faq). A [local Bot API server](https://core.telegram.org/bots/api#using-a-local-bot-api-server) raises uploads to 2000 MB | About 2 GB, derived from Telegram's [4000 parts](https://core.telegram.org/api/config) of 512 KB, not tested |
| Credentials | Bot token | Bot token plus [api_id and api_hash](https://docs.telethon.dev/en/stable/basic/signing-in.html), plus a session file |
| Flood limits | Raises `RetryAfter`. [`AIORateLimiter`](https://docs.python-telegram-bot.org/en/stable/telegram.ext.aioratelimiter.html) can retry | [Sleeps automatically](https://docs.telethon.dev/en/stable/concepts/errors.html) up to 60 s, then raises `FloodWaitError` |
| Latest release | [22.8, 2026-06-12](https://pypi.org/pypi/python-telegram-bot/json) | [1.46.0, 2026-11-17](https://pypi.org/pypi/Telethon/json) |
| Releases 2025 / 2026 | 9 / 3 | 6 / 6 |
| Commits, last 12 months | [172](https://github.com/python-telegram-bot/python-telegram-bot/commits/master), 48 of them by 15 people and the rest by bots | [63](https://codeberg.org/Lonami/Telethon/commits/branch/v1) by 24 author names, half by one maintainer |
| Repository | [GitHub](https://github.com/python-telegram-bot/python-telegram-bot), active | [GitHub archived](https://github.com/LonamiWebs/Telethon) on 2026-02-21 and "may be deleted". Now on [Codeberg](https://codeberg.org/Lonami/Telethon) |
| Downloads, last month | [7.6 M](https://pypistats.org/packages/python-telegram-bot) | [4.1 M](https://pypistats.org/packages/telethon) |
| API coverage | [Bot API 10.0](https://github.com/python-telegram-bot/python-telegram-bot#telegram-api-support). Telegram is at [10.5](https://core.telegram.org/bots/api-changelog) | Layer 233, updated [2026-11-05](https://codeberg.org/Lonami/Telethon/commits/branch/v1). Since v1.29 (2023) the friendly API aims to be ["feature-frozen"](https://docs.telethon.dev/en/stable/misc/changelog.html#more-bug-fixing-v1-29) while v1 is active |

Both have full reference docs. PTB's cover this project's stack directly (conversations, jobs, persistence). In my reading Telethon's bot guidance is thinner, and its PTB migration page still shows the [pre-v20 `Updater` API](https://docs.telethon.dev/en/stable/concepts/botapi-vs-mtproto.html).

### Performance

Nothing was measured, and I found no reliable benchmark. Telethon's wiki files "less overhead" under [anecdotal advantages "which we have no proof for"](https://codeberg.org/Lonami/Telethon/wiki/MTProto-vs-HTTP-Bot-API) and says it "doesn't really mean much" unless the Bot API server is slow or down.

It would not matter here. A listing can wait up to the whole scan interval, 5 to 60 minutes, before the bot sees it, and the scan then drives a browser through result pages. Saving part of a second on delivery is not visible. Button taps already arrive through [long polling](https://docs.python-telegram-bot.org/en/stable/telegram.ext.application.html), with a 0 s interval between polls. Throughput is a few messages per scan, more on the first.

### Credentials and session

[api_id](https://core.telegram.org/api/obtaining_api_id) is tied to a person's phone number, one per number, and accounts that log in through unofficial clients are "automatically put under observation". The page says "all accounts" and does not mention bots. Every self-hoster of this bot would need to register one on top of the BotFather token.

The [session file](https://docs.telethon.dev/en/stable/concepts/sessions.html) is a SQLite database holding the authorization key. It is a secret, must be in `.gitignore`, needs a volume under Docker (#13), and [cannot be used by two clients at once](https://docs.telethon.dev/en/stable/quick-references/faq.html). A `StringSession` avoids the file but is an equal secret. Losing it forces another token login. I found no published limit on how often a bot may do that.

### Migration, per file

| File | Change |
|---|---|
| `requirements.txt` | Telethon and APScheduler replace `python-telegram-bot[job-queue]`. `httpx` stays, `car_model_catalog.py` uses it |
| `src/common/config.py` | API id, API hash, session path, validation |
| `src/common/logger.py` | Mute `telethon` instead of `telegram` |
| `src/main.py` | `run_polling(drop_pending_updates=True)` becomes start plus `run_until_disconnected`. `catch_up=False` looks equivalent, not tested |
| `src/bot/bot.py` (81 lines) | Replace `ConversationHandler` with our own per-chat state dispatch, plus an error wrapper |
| `src/bot/handlers.py` (457) | 11 handler signatures, 36 lines of `context.chat_data` moved to a store we write, 11 Markdown calls, async sender lookup in `TelegramUserInfo` |
| `src/bot/keyboards.py` (122) | 18 `InlineKeyboardButton` calls, mechanical. Callback data arrives as bytes |
| `src/bot/scanner.py` (106) | Job context, job lookup and sends |
| `.gitignore`, `README.md`, `.claude/CLAUDE.md` | Session file, setup steps, conventions |

Two traps, both confirmed by running Telethon 1.46.0's parser. Its Markdown uses `**bold**`, so every `*Next*` would show literal asterisks, and it ignores backslash escapes, so `escape_markdown` output would show backslashes. And because Markdown is on by default, `https://www.yad2.co.il/item/a__b__c` becomes `.../item/abc` unless `parse_mode=None` is passed.

Issue #19 lists migration effort, but effort did not decide this.

## Decision

Stay on python-telegram-bot.

- Performance: unmeasured, and irrelevant at this scan interval.
- Features: everything the bot uses exists in PTB. Telethon has no job queue, no global error handler, and no conversation handler it recommends for bots. What Telethon adds (2 GB files, raw API, user accounts) is unused.
- Code simplicity: worse. We would own a state machine, a scheduler and an error handler that PTB maintains today.

Telethon is ahead on recent releases and API freshness. Neither touches a feature this bot uses.

## Consequences

- Deployment keeps needing one secret and no session state.
- #11 can build on `JobQueue`. #12 adds persistent storage (SQLite), which can sit behind PTB's [persistence interface](https://docs.python-telegram-bot.org/en/stable/telegram.ext.basepersistence.html) or bypass it.
- We accept PTB's lag. Its maintainers [paused Bot API 10.1 work on 2026-06-18](https://github.com/python-telegram-bot/python-telegram-bot/issues/5261#issuecomment-4744377159) until "major refactors" are done. The issue sits on the [v23 milestone](https://github.com/python-telegram-bot/python-telegram-bot/milestones), still open past its due date of 2026-09-01, and 22.8 is the last release. The bot uses only sends, edits and callback answers, which 22.6 already supports.
- The pin, 22.6, is two releases behind 22.8. Upgrading is separate work.
- Follow-up found while reading the code, not reproduced: `scanner.py` marks URLs as seen before sending them and has no flood retry, so a failed send loses the rest of that scan's listings. Telegram advises [one message per second per chat](https://core.telegram.org/bots/faq) and the first scan sends in a tight loop. Sending before marking and adding `AIORateLimiter(max_retries=...)` should fix this within PTB.

## Revisit if

- A feature needs a user account or data the Bot API does not expose, or files over 50 MB without a local Bot API server.
- PTB has no release by mid-2027, or is archived.
- Telegram removes or breaks a Bot API method PTB relies on before v23 ships.
- Telethon v2 reaches a stable release with conversation and scheduling support.
- Measured latency turns out to affect users.

## Sources

Read on 2026-11-23. The PyPI, GitHub and Codeberg figures are from that day and will drift. Library behaviour was checked against Telethon 1.46.0 and PTB 22.6 installed locally. The Telethon "stable" docs still show 1.45.0.

- PTB: [PyPI](https://pypi.org/pypi/python-telegram-bot/json), [docs](https://docs.python-telegram-bot.org/en/stable/), [repository](https://github.com/python-telegram-bot/python-telegram-bot), [Bot API 10.1 issue](https://github.com/python-telegram-bot/python-telegram-bot/issues/5261)
- Telethon: [PyPI](https://pypi.org/pypi/Telethon/json), [v1 docs](https://docs.telethon.dev/en/stable/), [v2 docs](https://docs.telethon.dev/en/v2/), [Codeberg](https://codeberg.org/Lonami/Telethon), [archived GitHub](https://github.com/LonamiWebs/Telethon)
- Telegram: [Bot API changelog](https://core.telegram.org/bots/api-changelog), [Bots FAQ](https://core.telegram.org/bots/faq), [api_id terms](https://core.telegram.org/api/obtaining_api_id), [client config](https://core.telegram.org/api/config)
- Downloads: [pypistats.org](https://pypistats.org/)
