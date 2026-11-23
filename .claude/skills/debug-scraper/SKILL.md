---
name: debug-scraper
description: How Yad2's car pages and APIs are built, and how to find out why a scan returns nothing, too little or wrong links. Use when a scan fails or times out, when Yad2 changes its layout, before editing car_finder.py, or when adding a search filter or catalog field.
---

# Debug the Yad2 scraper

Facts marked with a date were seen on live Yad2 that day. Check them again before relying on them,
and update the date here.

## Pages

- Search: `https://www.yad2.co.il/vehicles/cars?manufacturer=48&model=10711&year=2021-2022&page=2`.
  Ranges are `min-max`, with `-1` for no limit
- Ad: `https://www.yad2.co.il/vehicles/item/<id>`. Result links are `item/<id>` or `/item/<id>`,
  relative to `/vehicles` (2026-11-23)
- Result cards: `a[data-nagish='private-item-link']`, `a[data-nagish='agent-item-link']` and
  `a[data-nagish='agent-item-no-footer-link']`. They render while scrolling, so the scraper does not
  read them: a page of 40 ads once gave only 21 (2026-11-23)

## Embedded data

The scraper reads `<script id="__NEXT_DATA__">`: `props.pageProps.dehydratedState.queries`, the query
that has `pagination: {pages, perPage, total}` (2026-11-23).

- Two layouts are in use, sometimes within one search: the ads are in `private` and `commercial`, or
  in `ads`. Promoted ads repeat in `platinum`, `boost` and `solo`
- The layouts order ads differently, so page 2 can repeat ads of page 1 and skip others. The scraper
  warns when it collected fewer ads than `total`
- A search without results has `total: 0`
- Receivership sales have `externalKonesUrl`, a link to `konesy2.co.il` instead of a Yad2 page
- `customer` identifies the seller. Do not store or log it

## API

`https://gw.yad2.co.il/search-options/vehicles/cars` answers plain HTTP requests with a browser
`User-Agent` (2026-11-23):

- `?fields=manufacturer` - every manufacturer, as `{"text", "value"}` with Hebrew names
- `?fields=model&manufacturer=<id>` - that manufacturer's models

## When a scan fails

1. Run one narrow scan with `LOG_LEVEL=DEBUG` and read the last log line before the failure.
2. Look at the page the browser got: `location.href`, `document.title`, the first lines of
   `document.body.innerText` and `tab.save_screenshot(...)`.
   - Another host means the bot check. Stop and wait, do not retry in a loop
   - The right page without a feed (`FEED_ITEMS_NOT_FOUND`) means Yad2 changed its data. Look for the
     new query in `__NEXT_DATA__`
3. Fix `yad2_feed.py`, add the new shape to its tests, then run the live scan of the `verify` skill.

## Containers

`docker compose up` runs the bot the way users do. Without it: `podman build --format docker -t yad2-car-finder .`
and run it with `--init --shm-size 512m`. Chrome needs a display (`docker/entrypoint.sh` starts Xvfb) and
`CHROME_SANDBOX=false`. `xvfb-run` hangs as PID 1 and does not pass on the stop signal, so it is not
used in the image.
