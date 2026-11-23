---
name: verify
description: Check a change to Yad2 Car Finder before committing it - lint, tests, the real bot handlers and a live scan. Use before opening a pull request, after changing handlers, keyboards, the scanner or the scraper, or when asked whether a change works.
---

# Verify a change

Run the steps that match what changed. Report what ran and what did not.

## 1. Always

```bash
make check
```

Fix every finding, also ones the change did not cause. Cover new logic with tests that fail without
the change. Tests never reach the network: serve Yad2's responses with `httpx.MockTransport`.

## 2. Handlers or keyboards changed

Drive the real handlers, not copies of them: build the `Application` with a dummy token, feed it
`Update` objects through `process_update`, and stub only the network calls of the `Bot`. Walk the
full flow, from `/search` to the started scan, including Skip, Edit, paging and an unreachable
Yad2. Check that:

- every button's callback data matches a pattern in `bot.py`
- no keyboard exceeds 100 buttons, and no callback data exceeds 64 bytes
- text sent with `parse_mode` has Yad2's values escaped

## 3. Scraper or search filter changed

Run one live scan with a narrow filter (one model, two years), so it loads one or two pages.
Chrome needs a display: on a headless machine use `xvfb-run -a`. Never loop live scans, since Yad2's
bot check blocks the address. Then open two of the returned URLs and check that they are ads.

If the scan fails, continue with the `debug-scraper` skill.

## 4. Real Telegram chat

Needs `TELEGRAM_BOT_TOKEN`, which only the maintainer has. If it is not set, say in the pull
request that the change was not tried in a real chat.
