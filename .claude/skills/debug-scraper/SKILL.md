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
- Page load indicator: `a[data-nagish='feed-item-card-link']` (the recommendations load first)
- Results: `a[data-nagish='private-item-link']`, `a[data-nagish='agent-item-link']` and
  `a[data-nagish='agent-item-no-footer-link']`. They appear after scrolling down
- Agent cards repeat promoted ads, and some link to other sites such as `konesy2.co.il` (2026-11-23)
- Links with `spot=look_alike` are similar cars, not matches
- Pages: `nav[data-nagish='pagination-navbar']`, 40 results each
- Ad popup: an iframe titled "Modal Message", closed by `.bz-close-btn`

## Embedded data

`<script id="__NEXT_DATA__">` holds the results as JSON, under
`props.pageProps.dehydratedState.queries`, in the query whose key starts with `"feed"`. Its data
has the lists `platinum`, `boost`, `solo`, `commercial` and `private`, and
`pagination: {pages, perPage, total}` (2026-11-23). Compare `total` with what a scan collected to see
whether it missed ads.

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
   - "מה שחיפשת לא נמצא" means the search has no results
   - The right page without matches for a selector means Yad2 changed its layout. Find the new
     `data-nagish` values
3. Fix the selector, then run the live scan of the `verify` skill.

## Containers

Chrome needs a display (`xvfb-run -a`), an init process (`--init`, since `xvfb-run` hangs as PID 1),
`sandbox=False` in nodriver and at least 256 MB of `/dev/shm`.
