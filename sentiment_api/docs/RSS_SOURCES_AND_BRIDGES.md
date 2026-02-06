# RSS Sources and RSS-Bridge

**Full audit:** See [MEDIA_SOURCES_AUDIT.md](MEDIA_SOURCES_AUDIT.md) for a source-by-source report (wire services, broadcasters, business, Americas, Europe, MENA, Africa, Asia–Pacific) with registry status (native RSS, bridged, or not in registry) and next-step suggestions.

## New sources added (from requested URLs)

The following were checked and added to `registry/source_registry.yaml` under pack `optional_media_rss`:

| Source | Origin | Feed URL |
|--------|--------|----------|
| **FT News Feed** | [ft.com/news-feed](https://www.ft.com/news-feed) (hub page; FT RSS pattern) | `https://www.ft.com/?format=rss` |
| **Thomson Reuters IR Financial News** | [ir.thomsonreuters.com/rss-feeds](https://ir.thomsonreuters.com/rss-feeds) | `https://ir.thomsonreuters.com/rss/news-releases.xml?items=15` |
| **Thomson Reuters IR Event Calendar** | Same page | `https://ir.thomsonreuters.com/rss/events.xml?items=15` |
| **Thomson Reuters IR SEC Filings** | Same page | `https://ir.thomsonreuters.com/rss/sec-filings.xml?items=15` |
| **Reuters Top News** | [gist stungeye](https://gist.github.com/stungeye/fe88fc810651174d0d180a95d79a8d97) | `https://feeds.reuters.com/reuters/topNews` |
| **Time Top Stories** | Same gist | `https://time.com/feed/` |
| **MarketWatch Top Stories** | Same gist | `https://feeds.marketwatch.com/marketwatch/topstories/` |
| **Yahoo Finance News (RSS Index)** | [finance.yahoo.com/news/rssindex](https://finance.yahoo.com/news/rssindex) | `https://finance.yahoo.com/news/rssindex` |

**Note:** The FT news-feed page itself may return a client challenge when fetched headless; the feed URL above uses FT’s standard RSS pattern and is the one to use for ingestion.

## External curated feed lists (references)

You can add more feeds by converting entries from these lists into `source_registry.yaml` entries (same format as above: `source_id`, `name`, `type: rss`, `feed_url`, etc.):

- **[stungeye/crypto_news.json (gist)](https://gist.github.com/stungeye/fe88fc810651174d0d180a95d79a8d97)** – JSON list of `{ "url", "rss" }` for many news sites (CNN, NYT, Reuters, FT, etc.). Use the `rss` value as `feed_url`; skip empty `rss`.
- **[plenaryapp/awesome-rss-feeds](https://github.com/plenaryapp/awesome-rss-feeds)** – OPML and markdown by country and category (~500 recommended, 250+ by country). Use “Primary Feed Url” or “RSS Feed Url” as `feed_url`.
- **[joshuawalcher/rssfeeds](https://github.com/joshuawalcher/rssfeeds)** – Curated list of active RSS feeds (News, Sports, Tech, Business, etc.). Map names to feed URLs (e.g. from the gist or plenary list) when adding.

The daemon and workers use `registry/source_registry.yaml` (or `SOURCE_REGISTRY_PATH`). Add new sources there and restart/scale workers as needed.

## RSS-Bridge

**[RSS-Bridge](https://rss-bridge.github.io/rss-bridge/)** is a PHP project that generates RSS/Atom feeds for sites that do not offer them (e.g. Google News, Twitter/X, Instagram, YouTube). It is not a feed list; it is a service that creates feeds on demand.

### Running RSS-Bridge in this project

The stack includes an **optional** `rss-bridge` service:

- **Docker Compose:** The service is defined in `docker-compose.yml`. Start it with the rest of the stack: `docker compose up -d`. RSS-Bridge listens on host port **8085** (http://localhost:8085); workers and daemon use the internal URL `http://rss-bridge/` when ingesting.
- **Enable ingestion:** In `registry/source_registry.yaml` set `optional_media_rss_bridge: { enabled: true }` under `packs`, then restart the daemon/workers.

### Major reputable media (bridged AP, Reuters, etc.)

| Source | Bridge | Notes |
|--------|--------|--------|
| **Google News** | CssSelector | Home page → article links. No official RSS. |
| **Google Search “news”** | GoogleSearch | Search results for “news”. |
| **AllSides Headline Roundups** | AllSides | Balanced headlines and bias ratings; no native RSS. |
| **AP Top News / Business / World** | AssociatedPressNews | AP has no general public RSS; bridge uses their API. |
| **Reuters Top News / Business / Markets** | Reuters | Alternative to native Reuters RSS; more sections (Business, Markets, etc.). |

You already have **native** Reuters Top News in the registry (`reuters_top_news`). The bridged Reuters feeds are optional alternatives or for extra sections (e.g. Markets, Business).

### 403 fallbacks (native feed returns 403)

Some registry feeds can return **403 Forbidden** when fetched (e.g. from certain networks or without a browser). Bridged alternatives are available so ingestion still works when RSS-Bridge is running:

| Native source | Bridged alternative | Bridge |
|---------------|---------------------|--------|
| **BLS RSS** (`us_bls_rss`) — https://www.bls.gov/feed/ | BLS Economic News Releases | CssSelector on news releases page |
| **EU Council RSS** (`eu_council_rss`) — https://www.consilium.europa.eu/en/about-site/rss/ | EU Council Press Releases | CssSelector on press releases page |

Run `python3 scripts/check_feed_status.py --only-403` to list sources that currently return 403; add CssSelector (or another bridge) entries for any you want to back up via RSS-Bridge.

These are registered as normal RSS sources under pack `optional_media_rss_bridge` with `feed_url` pointing at `http://rss-bridge/?action=display&bridge=…&format=Rss&…`. They only work when the `rss-bridge` service is running and the pack is enabled.

### Adding more bridges

1. **Run RSS-Bridge** (Docker above or [public host](https://rss-bridge.github.io/rss-bridge/Public_Hosts.html)).
2. Use the web UI (e.g. http://localhost:8085) to pick a bridge (e.g. CssSelector, TheGuardian, NPR), set parameters, and get the feed URL.
3. **Add that URL to** `source_registry.yaml`:
   - `type: rss`
   - `feed_url: "http://rss-bridge/…"` (same host as workers) or your instance URL
   - Put the source in pack `optional_media_rss_bridge` or another pack as desired.

RSS-Bridge does not replace the registry; it produces feed URLs that you register like any other RSS source. Respect rate limits and ToS of the bridged sites.

### References

- [RSS-Bridge For Developers](https://rss-bridge.github.io/rss-bridge/For_Developers/index.html)
- [Project goals](https://rss-bridge.github.io/rss-bridge/Project-goals.html) and [Public Hosts](https://rss-bridge.github.io/rss-bridge/Public_Hosts.html) (if you don’t self-host)
- [Bridge list (GitHub)](https://github.com/RSS-Bridge/rss-bridge/tree/master/bridges) — e.g. NYT, TheGuardian, Reuters, NPR, CssSelector for any site
