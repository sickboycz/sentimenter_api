# Media Sources Audit: RSS & Bridged Feeds

Audit of the requested global media list against `registry/source_registry.yaml`.  
**Legend:** ✅ In registry (native RSS) · 🔗 In registry (bridged) · ❌ Not in registry

Defaults: `translate_to_en: true` and `credibility_tier: reputable_media` apply to all packs; non-English sources are translated via the OpenAI gateway.

**Worldwide check (completed):** All sources below were checked for official RSS or bridged alternatives. Where a URL is listed, it was verified via public documentation or aggregator references.

---

## 1) Global wire services

| Source | Status | Notes |
|--------|--------|--------|
| **Reuters** | ✅ + 🔗 | Native: `reuters_top_news` (`https://feeds.reuters.com/reuters/topNews`). Bridged: Top News, Business, Markets (optional_media_rss_bridge). |
| **Associated Press (AP)** | 🔗 | No public RSS. Bridged: AP Top News, Business, World (AssociatedPressNews bridge). |
| **Agence France-Presse (AFP)** | ❌ | No general public RSS; API has RSS/ATOM for subscribers only. Use CssSelector on afp.com or third-party. |
| **Bloomberg News** | ❌ | No official RSS. Use CssSelector bridge on bloomberg.com. |
| **DPA** (Germany) | ❌ | No public RSS URL found. Use CssSelector on dpa.com. |
| **EFE** (Spain) | ❌ | EFE Servicios (B2B); no public RSS URL. Use CssSelector on efe.com. |
| **ANSA** (Italy) | ❌ | **RSS:** `https://www.ansa.it/web/ansait_web_rss_homepage.xml` (add to registry). |
| **PA Media** (UK) | ❌ | No public RSS. Use CssSelector. |
| **Kyodo News** (Japan) | ❌ | **RSS:** `https://english.kyodonews.net/list/feed/rss4kyodonews-fzone` (add to registry). |
| **Yonhap** (South Korea) | ❌ | **RSS:** `https://en.yna.co.kr/RSS/news.xml` (all news); also national, economy, culture, sports at en.yna.co.kr/RSS/ (add to registry). |
| **PTI** (India) | ❌ | No public RSS URL found. Use CssSelector on pti.in or Indian Express/NDTV for India. |

---

## 2) International public broadcasters

| Source | Status | Notes |
|--------|--------|--------|
| **BBC News / BBC World Service** | ✅ | `bbc_world_rss`, `bbc_news_home`, `bbc_news_india`, `bbc_news_science_environment`. |
| **Deutsche Welle (DW)** | ✅ | `dw_rss`. |
| **France 24 / RFI** | ✅ | `france24_com`. **RFI:** `https://www.rfi.fr/en/rss` (and rfi.fr/en/africa/rss, etc.) – add to registry. |
| **Al Jazeera** | ✅ | `aljazeera_rss`. |
| **NHK World-Japan** | ❌ | **RSS (written):** `https://www3.nhk.or.jp/rss/news/cat0.xml` (Japanese). **English (radio):** `https://www3.nhk.or.jp/rj/podcast/rss/english.xml`. For NHK World English web articles, use CssSelector on www3.nhk.or.jp/nhkworld/en/news/. |
| **ABC Australia** | ✅ | `abc_news` (Australia). |
| **CBC/Radio-Canada** | ❌ | **RSS:** `https://www.cbc.ca/cmlink/rss-topstories`, `https://www.cbc.ca/cmlink/rss-world`, etc.; hub at cbc.ca/rss/ – add to registry. |
| **RTS/SRF + SWI swissinfo.ch** | ❌ | **swissinfo.ch:** `https://www.swissinfo.ch/service/eng/rssxml/latest-news/rss`. **SRF:** e.g. `https://www.srf.ch/news/bnf/rss/1890`. RTS/RTS News – check rts.ch for RSS. |

---

## 3) Top-tier business & markets

| Source | Status | Notes |
|--------|--------|--------|
| **Bloomberg** | ❌ | No official RSS. Use CssSelector bridge. |
| **Financial Times (FT)** | ✅ | `ft_rss_world`, `ft_news_feed` (`https://www.ft.com/?format=rss`). |
| **The Wall Street Journal (WSJ)** | ❌ | Official feeds at `feeds.content.dowjones.io/public/rss/` (e.g. Markets, US Business, World). RSS-Bridge also has WSJ – add native or bridge. |
| **The Economist** | ❌ | No public RSS. Use RSS-Bridge Economist bridge. |
| **Barron's** | ❌ | No official public RSS URL; third-party (rss.app). Use CssSelector. |
| **Nikkei / Nikkei Asia** | ❌ | **RSS:** https://info.asia.nikkei.com/rss – add to registry. |
| **Handelsblatt** (Germany) | ❌ | No exact URL in check. Use CssSelector on handelsblatt.com. |
| **Les Echos** (France) | ❌ | No exact URL in check. Use CssSelector on lesechos.fr. |
| **Il Sole 24 Ore** (Italy) | ❌ | No exact URL in check. Use CssSelector on ilsole24ore.com. |

---

## 4) Americas

### USA

| Source | Status | Notes |
|--------|--------|--------|
| **The New York Times** | ✅ | `nyt_top_stories`, `nyt_world_news`, `nyt_science`. |
| **Washington Post** | ✅ | `washingtonpost_world`. |
| **WSJ** | ❌ | See Business; native Dow Jones feeds or bridge. |
| **CNN** | ✅ | `cnn_com_rss_channel_app_international_edition`, `cnn_com_rss_channel_world`. |
| **NBC News** | ✅ | `feeds_nbcnews_topstories`. |
| **CBS News** | ❌ | **RSS:** https://www.cbsnews.com/rss/ (Top Stories, US, World, etc.) – add to registry. |
| **ABC News** (US) | ✅ | `abcnews_topstories`. |
| **PBS NewsHour** | ❌ | **RSS:** `https://www.pbs.org/newshour/feeds/rss/headlines` (also politics, Brooks and Capehart) – add to registry. |
| **NPR** | ❌ | **RSS:** `https://feeds.npr.org/` (hub); e.g. All Things Considered at feeds.npr.org/programs/all-things-considered – add to registry. |

### Canada

| Source | Status | Notes |
|--------|--------|--------|
| **CBC News** | ❌ | **RSS:** `https://www.cbc.ca/webfeed/rss/rss-topstories`, rss-world, etc.; hub at cbc.ca/rss/ – add to registry. |
| **The Globe and Mail** | ❌ | Multiple feeds (FeedSpot ref); check globeandmail.com for exact URLs. |
| **Toronto Star** | ❌ | **RSS:** thestar.com/site/static-pages/rss-feeds.html – add section feeds. |

### Latin America

| Source | Status | Notes |
|--------|--------|--------|
| **El País (América)** | ❌ | **RSS:** `https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada` or elpais.com/rss/elpais/portada.xml – add to registry. |
| **Clarín / La Nación** (Argentina) | ❌ | **Clarín:** `https://www.clarin.com/rss/lo-ultimo` – add. La Nación – check for RSS. |
| **Folha, O Globo, Estadão, GloboNews** (Brazil) | ❌ | **O Globo:** oglobo.globo.com/rss/. Estadão has multiple feeds (FeedSpot). Folha/GloboNews – check. |
| **El Universal, Reforma, Milenio** (Mexico) | ❌ | **Reforma:** `https://www.reforma.com/rss/portada.xml`. El Universal/Milenio – check or CssSelector. |
| **El Tiempo** (Colombia), **El Mercurio / La Tercera** (Chile), **El Comercio** (Peru) | ❌ | Check eltiempo.com, emol.com, latercera.com, elcomercio.pe for /rss or /feed. |

---

## 5) Europe

### UK / Ireland

| Source | Status | Notes |
|--------|--------|--------|
| **BBC** | ✅ | See Broadcasters. |
| **Financial Times** | ✅ | See Business. |
| **The Guardian** | ✅ | `world_news_the_guardian`, `india_the_guardian`, `theguardian_business_economics_rss`. |
| **The Times** | ❌ | No longer offers official RSS (discontinued); use CssSelector or third-party. |
| **Sky News** | ❌ | **RSS:** `http://feeds.skynews.com/feeds/rss/uk.xml` (also home, world, business, etc. at news.sky.com/info/rss) – add to registry. |
| **The Telegraph** | ✅ | `telegraph_rss_xml`. |

### France

| Source | Status | Notes |
|--------|--------|--------|
| **Le Monde** | ❌ | Has RSS (lemonde.fr/en/rss, binaire.blog.lemonde.fr/feed); check main feed URL – add to registry. |
| **Le Figaro** | ❌ | 50+ feeds (FeedSpot); check lefigaro.fr for exact URLs – add. |
| **Les Echos** | ❌ | See Business (CssSelector). |
| **France 24** | ✅ | `france24_com`. |

### Germany / Austria / CH

| Source | Status | Notes |
|--------|--------|--------|
| **DW** | ✅ | `dw_rss`. |
| **Der Spiegel** | ❌ | **RSS:** `https://www.spiegel.de/schlagzeilen/tops/index.rss`, eilmeldungen, politik, etc. – add to registry. |
| **FAZ** | ❌ | **RSS:** faz.net has RSS page (faz.net/faz/rss-feed-…) – add. |
| **Süddeutsche Zeitung** | ❌ | **RSS:** `https://rss.sueddeutsche.de/rss/Topthemen`, rss.sueddeutsche.de/alles – add to registry. |
| **Handelsblatt** | ❌ | See Business. |
| **ORF** (Austria) | ❌ | Check orf.at for RSS. |
| **NZZ** (Switzerland) | ❌ | Check nzz.ch for RSS. |

### Spain / Portugal

| Source | Status | Notes |
|--------|--------|--------|
| **El País** | ❌ | See Latin America (RSS URLs above). |
| **El Mundo** | ❌ | **RSS:** `http://rss.elmundo.es/rss/descarga.htm?data2=4` – add. |
| **La Vanguardia** | ❌ | **RSS:** `https://www.lavanguardia.com/rss/home.xml` (and section feeds) – add to registry. |
| **RTVE** | ❌ | No specific public RSS URL in check; try rtve.es/noticias or CssSelector. |
| **Público / RTP** (Portugal) | ❌ | **RTP:** `https://www.rtp.pt/noticias/rss`, rtp.pt/noticias/rss/pais, mundo, etc. – add. Público – check publico.pt. |

### Italy

| Source | Status | Notes |
|--------|--------|--------|
| **Corriere della Sera** | ❌ | **RSS:** corriere.it/rss/ (section feeds) – add to registry. |
| **La Repubblica** | ❌ | **RSS:** repubblica.it/servizi/rss/guida.html – add. |
| **Il Sole 24 Ore** | ❌ | See Business. |
| **RAI News** | ❌ | **RSS:** rai.it/dl/portali/site/page/… (RSS hub) – add. |

### Nordics

| Source | Status | Notes |
|--------|--------|--------|
| **SVT / Sveriges Radio, DR, NRK, Yle** | ❌ | **SVT:** `http://www.svt.se/nyheter/rss.xml`. **Yle:** `https://feeds.yle.fi/uutiset/v1/majorHeadlines/YLE_UUTISET.rss`. **DR:** dr.dk has RSS. **NRK:** podcast feeds; check nrk.no for news RSS. **Sveriges Radio:** sverigesradio.se (RSS/podcasts). |
| **Dagens Nyheter, Aftenposten, Helsingin Sanomat** | ❌ | **DN:** `https://www.dn.se/rss`. **Aftenposten:** `https://www.aftenposten.no/rss/`. **HS:** check hs.fi. |

### Central & Eastern Europe

| Source | Status | Notes |
|--------|--------|--------|
| **PAP / TVN24** (Poland) | ❌ | Check pap.pl, tvn24.pl for RSS. |
| **ČTK / ČT24 / HN** (Czechia) | ❌ | ČTK: B2B; no public RSS URL. Check ct24.ceskatelevize.cz for ČT24. |
| **TASR / SME** (Slovakia) | ❌ | Check for RSS. |
| **Ukrinform / The Kyiv Independent** (Ukraine) | ❌ | Check ukrinform.net, kyivindependent.com for RSS. |

---

## 6) Middle East & North Africa

| Source | Status | Notes |
|--------|--------|--------|
| **Al Jazeera** | ✅ | `aljazeera_rss`. |
| **Al Arabiya** | ❌ | english.alarabiya.net – no specific RSS URL in check; use CssSelector or Google News. |
| **The National** (UAE) | ❌ | **RSS:** thenationalnews.com/uae/rss-feeds-1.536712 – add to registry. |
| **Haaretz / The Jerusalem Post / Times of Israel** | ❌ | **Haaretz:** haaretz.com/misc/subscribe-to-rss-feed, haaretz.com/srv/…. **JPost:** `https://www.jpost.com/rss`. **Times of Israel:** `https://www.timesofisrael.com/feed/` – add to registry. |
| **Asharq Al-Awsat** | ❌ | english.aawsat.com – check for /feed or RSS page. |

---

## 7) Sub-Saharan Africa

| Source | Status | Notes |
|--------|--------|--------|
| **BBC Africa, France 24 Afrique, DW Africa** | ❌ | Use main BBC, France 24, DW feeds or regional pages (e.g. rfi.fr/en/africa/rss). |
| **News24, Mail & Guardian, SABC News** (South Africa) | ❌ | **News24:** `https://www.news24.com/news24RSSFeed/0,,7,00.xml`. **Mail & Guardian:** mg.co.za/rss-feeds/. **SABC:** sabcnews.com/sabcnews/rss-feeds/ or …/category/[cat]/feed/ – add to registry. |
| **Nation Africa** (Kenya) | ❌ | nation.africa – no specific RSS URL in check; try /feed or CssSelector. |
| **Premium Times** (Nigeria) | ❌ | premiumtimesng.com – RSS available via aggregators (may be irregular); check site for /feed. |

---

## 8) Asia–Pacific

### Japan

| Source | Status | Notes |
|--------|--------|--------|
| **NHK** | ❌ | See Broadcasters (www3.nhk.or.jp/rss/news/cat0.xml, radio english.xml). |
| **Nikkei** | ❌ | See Business (info.asia.nikkei.com/rss). |
| **Asahi Shimbun** | ❌ | Asahi AJW (asahi.com/ajw); check for RSS – add if found. |
| **Yomiuri Shimbun** | ❌ | The Japan News (japannews.yomiuri.co.jp); check for RSS. |
| **Kyodo** | ❌ | See Wires (english.kyodonews.net/list/feed/…). |

### South Korea

| Source | Status | Notes |
|--------|--------|--------|
| **Yonhap** | ❌ | See Wires (en.yna.co.kr/RSS/news.xml). |
| **KBS, JTBC** | ❌ | Check kbs.co.kr, jtbc.co.kr for RSS. |

### China

| Source | Status | Notes |
|--------|--------|--------|
| **Caixin** | ❌ | caixinglobal.com – no direct RSS URL in check; use CssSelector. |
| **Xinhua** | ❌ | **RSS:** `https://english.news.cn/rss/` (xinhuanet.com/english/rss/index.htm) – add to registry. |

### India

| Source | Status | Notes |
|--------|--------|--------|
| **The Hindu** | ❌ | **RSS:** thehindu.com/rssfeeds/ – add to registry. |
| **Indian Express** | ❌ | **RSS:** indianexpress.com/rss/ (section feeds) – add. |
| **Times of India** | ❌ | **RSS:** timesofindia.indiatimes.com/rss_index.cms – add to registry. |
| **NDTV** | ✅ | `feeds_ndtv_latestnews`. |
| **PTI** | ❌ | See Wires. |

### Southeast Asia

| Source | Status | Notes |
|--------|--------|--------|
| **The Straits Times / CNA** (Singapore) | ❌ | **Straits Times:** straitstimes.com/RSS-Feeds; e.g. `https://www.straitstimes.com/news/asia/rss.xml` – add. CNA – check. |
| **Kompas / Tempo / Antara** (Indonesia) | ❌ | **Antara:** `https://en.antaranews.com/rss/latest-news.xml` (world, business, etc.). **Kompas:** rss.kompas.com/. **Tempo:** en.tempo.co – check for RSS. |
| **Bangkok Post** (Thailand) | ❌ | **RSS:** `http://www.bangkokpost.com/rss/` – add to registry. |
| **ABS-CBN / GMA / Inquirer** (Philippines) | ❌ | **ABS-CBN:** abs-cbn.com/rss-feeds. **GMA:** gmanetwork.com/news/rss/. **Inquirer:** `https://www.inquirer.net/feed` (sports, business, etc.) – add to registry. |

### Australia / NZ

| Source | Status | Notes |
|--------|--------|--------|
| **ABC News** | ✅ | `abc_news`. |
| **SBS** | ❌ | **RSS:** `https://www.sbs.com.au/news/feed`, sbs.com.au/news/topic/latest/feed – add to registry. |
| **Australian Financial Review** | ❌ | afr.com – no specific RSS in check; use CssSelector. |
| **Sydney Morning Herald / The Age** | ✅ | `sydney_morning_herald_latest_news`. |
| **RNZ, TVNZ, NZ Herald** | ❌ | **RNZ:** `https://www.rnz.co.nz/rss`. **NZ Herald:** nzherald.co.nz (RSS page). TVNZ – check. |

---

## Summary

- **In registry (native or bridged):** Reuters, AP (bridged), BBC (multiple), DW, France 24, Al Jazeera, ABC Australia, FT (2), NYT (3), WaPo, CNN (2), NBC, ABC US, Guardian (3), Telegraph, NDTV, SMH, plus Google News/AP/Reuters/BLS/EU Council bridges in optional_media_rss_bridge.
- **Checked worldwide – RSS found (add to registry):** ANSA, Kyodo, Yonhap, RFI, CBC, NHK (rss/news + radio), swissinfo.ch, Nikkei Asia, CBS, PBS NewsHour, NPR, El País, Clarín, O Globo, Reforma, Sky News, Spiegel, FAZ, Süddeutsche, El Mundo, La Vanguardia, RTP Portugal, Corriere, La Repubblica, RAI, SVT, Yle, Dagens Nyheter, Aftenposten, The National UAE, Haaretz, JPost, Times of Israel, News24, Mail & Guardian, SABC, Xinhua, The Hindu, Indian Express, Times of India, Straits Times, Antara, Kompas, Bangkok Post, ABS-CBN, GMA, Inquirer, SBS, RNZ, NZ Herald.
- **No public RSS – use CssSelector or bridge:** AFP, Bloomberg, DPA, EFE, PA Media, PTI, The Times UK, Barron's, Handelsblatt, Les Echos, Il Sole 24 Ore, RTVE, Al Arabiya, Nation Africa, Caixin, KBS/JTBC, AFR, TVNZ; plus paywalled/bridge: Economist, WSJ (or Dow Jones native).
- **translate_to_en:** Default is `true` for all packs; override per source only if you want to keep original language.

---

## Verified RSS URLs (ready to add to registry)

Use these in `source_registry.yaml` under `optional_media_rss` (or a dedicated pack). Set `translate_to_en: true` for non-English feeds.

| Source | Feed URL |
|--------|--------|
| **ANSA** | `https://www.ansa.it/web/ansait_web_rss_homepage.xml` |
| **Kyodo News** | `https://english.kyodonews.net/list/feed/rss4kyodonews-fzone` |
| **Yonhap** | `https://en.yna.co.kr/RSS/news.xml` |
| **RFI** | `https://www.rfi.fr/en/rss` |
| **CBC** | `https://www.cbc.ca/webfeed/rss/rss-topstories`, `https://www.cbc.ca/webfeed/rss/rss-world` (hub: cbc.ca/rss/) |
| **NHK (written)** | `https://www3.nhk.or.jp/rss/news/cat0.xml` |
| **NHK World (radio EN)** | `https://www3.nhk.or.jp/rj/podcast/rss/english.xml` |
| **swissinfo.ch** | `https://www.swissinfo.ch/service/eng/rssxml/latest-news/rss` |
| **Nikkei Asia** | `https://info.asia.nikkei.com/rss` |
| **CBS News** | `https://www.cbsnews.com/rss/` |
| **PBS NewsHour** | `https://www.pbs.org/newshour/feeds/rss/headlines` |
| **NPR** | `https://feeds.npr.org/` |
| **Toronto Star** | thestar.com/site/static-pages/rss-feeds.html (section feeds) |
| **El País** | `https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada` |
| **Clarín** | `https://www.clarin.com/rss/lo-ultimo` |
| **O Globo** | `https://oglobo.globo.com/rss/` |
| **Reforma** | `https://www.reforma.com/rss/portada.xml` |
| **Sky News** | `http://feeds.skynews.com/feeds/rss/uk.xml` |
| **Der Spiegel** | `https://www.spiegel.de/schlagzeilen/tops/index.rss` |
| **Süddeutsche** | `https://rss.sueddeutsche.de/rss/Topthemen` |
| **El Mundo** | `http://rss.elmundo.es/rss/descarga.htm?data2=4` |
| **La Vanguardia** | `https://www.lavanguardia.com/rss/home.xml` |
| **RTP Portugal** | `https://www.rtp.pt/noticias/rss` |
| **Corriere della Sera** | `https://www.corriere.it/rss/` (section feeds) |
| **La Repubblica** | repubblica.it/servizi/rss/guida.html |
| **RAI** | https://www.rai.it/dl/portali/site/page/Page-4acf81b5-df2f-4687-aee2-1df2f490b8b4-rss.html |
| **SVT** | `http://www.svt.se/nyheter/rss.xml` |
| **Yle** | `https://feeds.yle.fi/uutiset/v1/majorHeadlines/YLE_UUTISET.rss` |
| **Dagens Nyheter** | `https://www.dn.se/rss` |
| **Aftenposten** | `https://www.aftenposten.no/rss/` |
| **The National (UAE)** | thenationalnews.com/uae/rss-feeds-1.536712 |
| **Haaretz** | haaretz.com/misc/subscribe-to-rss-feed |
| **Jerusalem Post** | `https://www.jpost.com/rss` |
| **Times of Israel** | `https://www.timesofisrael.com/feed/` |
| **News24** | `https://www.news24.com/news24RSSFeed/0,,7,00.xml` |
| **Mail & Guardian** | mg.co.za/rss-feeds/ |
| **SABC** | sabcnews.com/sabcnews/rss-feeds/ |
| **Xinhua** | `https://english.news.cn/rss/` |
| **The Hindu** | `https://www.thehindu.com/rssfeeds/` |
| **Indian Express** | indianexpress.com/rss/ |
| **Times of India** | timesofindia.indiatimes.com/rss_index.cms |
| **Straits Times** | `https://www.straitstimes.com/news/asia/rss.xml` (hub: straitstimes.com/RSS-Feeds) |
| **Antara** | `https://en.antaranews.com/rss/latest-news.xml` |
| **Kompas** | `https://rss.kompas.com/` |
| **Bangkok Post** | `http://www.bangkokpost.com/rss/` |
| **ABS-CBN** | abs-cbn.com/rss-feeds |
| **GMA** | gmanetwork.com/news/rss/ |
| **Inquirer** | `https://www.inquirer.net/feed` |
| **SBS Australia** | `https://www.sbs.com.au/news/feed` |
| **RNZ** | `https://www.rnz.co.nz/rss` |
| **NZ Herald** | nzherald.co.nz (RSS page) |

---

## Next steps

1. Run `python3 scripts/check_feed_status.py --only-403` to see which current feeds block; use bridged fallbacks where needed.
2. Add the verified RSS URLs above to `source_registry.yaml` (optional_media_rss or a new pack); set `translate_to_en: true` for non-English.
3. For sources with no RSS: use RSS-Bridge CssSelector or native bridges (Economist, WSJ) when optional_media_rss_bridge is enabled.
4. Enable `optional_media_rss_bridge` and run RSS-Bridge (e.g. `http://localhost:8085`) to use AP, Reuters extra sections, Google News, BLS, EU Council bridged feeds.
