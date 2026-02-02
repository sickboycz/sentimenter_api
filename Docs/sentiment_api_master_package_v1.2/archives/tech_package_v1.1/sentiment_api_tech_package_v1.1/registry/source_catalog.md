# Source Catalog (Global Coverage) — v1.0

This catalog defines *what “complete global coverage” means in practice*:

1) **Global firehose**: GDELT DOC 2.0 provides multilingual worldwide media monitoring (major+minor outlets).
2) **High-signal direct sources**: official institutions + structured datasets.
3) **Optional direct RSS**: major public media RSS for redundancy / lower latency.

> You do NOT need a static list of “every newspaper on earth” — GDELT covers breadth.
> The registry focuses on the sources that are (a) authoritative, and (b) systematically market-moving.

---

## A) Global firehose (breadth)
- GDELT DOC 2.0 (query profiles by topic + region)

Recommended query strategy:
- Always run global queries for:
  - rates/central banks
  - inflation/CPI
  - recession/growth
  - war/conflict escalation
  - sanctions/export controls
  - shipping disruptions
  - oil/gas supply shocks
- Additionally run *region-focused* queries, rotating by day of week:
  - Asia (CN/JP/KR/IN)
  - Europe (EU/GB/UA/RU)
  - Middle East (shipping/energy)
  - LatAm (Brazil/Argentina/Venezuela)
  - Africa (conflict & commodities)

---

## B) Official Macro & Central Banks (high-signal)

### “Must include” central banks (starter set)
- US: Federal Reserve (Fed)
- EU: European Central Bank (ECB)
- UK: Bank of England (BoE)
- Japan: Bank of Japan (BoJ)
- China: People’s Bank of China (PBoC)
- Canada: Bank of Canada (BoC)
- Australia: Reserve Bank of Australia (RBA)
- Switzerland: Swiss National Bank (SNB)
- New Zealand: Reserve Bank of New Zealand (RBNZ)
- Sweden: Riksbank
- Norway: Norges Bank
- Korea: Bank of Korea
- India: Reserve Bank of India
- Brazil: Banco Central do Brasil
- Mexico: Banco de México
- South Africa: South African Reserve Bank
- Turkey: Central Bank of the Republic of Türkiye

Implementation: prefer RSS if available; otherwise scrape “press releases”, “speeches”, “minutes”, “statements”.

> For full global expansion: add the BIS directory of central bank websites as a discovery seed, then scrape each site for press-release pages and RSS feeds.

### “Must include” statistics agencies (starter set)
- US: BLS / BEA / Census
- EU: Eurostat
- UK: ONS
- Canada: Statistics Canada
- Japan: Statistics Bureau
- China: National Bureau of Statistics
- etc.

---

## C) Politics & Geopolitics (high-signal)

### International institutions
- UN (General Assembly + Security Council updates)
- NATO news/press
- EU Council/Commission press
- G7/G20 communiqués (scrape the host/official pages per year)

### Major foreign affairs / defense ministries (starter set)
- US State Department updates
- UK Foreign, Commonwealth & Development Office
- France Ministry for Europe and Foreign Affairs
- Germany Federal Foreign Office
- Japan Ministry of Foreign Affairs
- India Ministry of External Affairs
- China Ministry of Foreign Affairs (English pages)
- Russia MFA (if accessible; may require careful compliance)
- Israel MFA, Saudi MFA, Iran MFA (English pages if available)
- Türkiye MFA

> Approach: Use GDELT for broad media coverage, and direct government sources to anchor credibility and confirm policy actions.

---

## D) Sanctions / export controls
Treat sanctions as *structured events* (not just news text).
Key sources:
- UN consolidated list updates
- US Treasury/OFAC recent actions
- UK sanctions list
- EU sanctions map / official EU journal releases

---

## E) Conflict / humanitarian datasets
Complement news with structured event data:
- ACLED (keyed API; conflict events)
- UCDP (conflict datasets)
- ReliefWeb (humanitarian/disaster alerts)
- International Crisis Group feeds

---

## F) Energy / nuclear / supply chain shocks
- EIA (inventories, short-term energy outlook)
- IAEA alerts (nuclear incidents/safeguards)
- OPEC press releases
- IRENA

Optional expansions:
- IEA (often gated; use if licensed)
- maritime chokepoints: Suez, Bab el-Mandeb, Strait of Hormuz incident trackers

---

## G) Optional major public media RSS (redundancy)
Enabled only if you want direct RSS beyond GDELT:
- BBC World
- Al Jazeera
- DW
- France24
- Reuters/AFP/AP (only if you have a licensed feed / allowed RSS)

---

## Appendix: Country Pack Template
See `country_pack_template.yaml`.

