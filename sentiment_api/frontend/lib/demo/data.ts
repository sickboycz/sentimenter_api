export const demo = {
  health: {
    status: "ok",
    as_of: new Date().toISOString(),
    checks: [
      { name: "api", status: "ok" },
      { name: "postgres", status: "ok" },
      { name: "redis", status: "ok" }
    ]
  },
  status: {
    api: "ok",
    ingestion: "ok",
    allocation: "ok",
    research: "unknown",
    as_of: new Date().toISOString(),
  },
  ops: {
    queues: { ingest: 28, summarize: 6, index: 2, normalize: 0, score: 0 },
    queues_total: 36,
    counts: { articles: 1240, clusters: 86, events: 86, summaries: 980, runs: 4200 },
    latest: {
      article_at: new Date(Date.now() - 2 * 60_000).toISOString(),
      cluster_at: new Date(Date.now() - 6 * 60_000).toISOString(),
      event_at: new Date(Date.now() - 8 * 60_000).toISOString()
    },
    runs: {
      ingest: {
        run_type: "ingest",
        status: "ok",
        started_at: new Date(Date.now() - 3 * 60_000).toISOString(),
        ended_at: new Date(Date.now() - 2 * 60_000).toISOString(),
        stats: { items_pushed: 34 }
      },
      summarize: {
        run_type: "summarize",
        status: "ok",
        started_at: new Date(Date.now() - 2 * 60_000).toISOString(),
        ended_at: new Date(Date.now() - 90_000).toISOString(),
        stats: { article_id: "art_demo_1" }
      }
    },
    heartbeats: {
      worker: {
        last_seen: new Date().toISOString(),
        age_sec: 2.4,
        last_job: { queue: "sentiment_api:ingest", at: new Date(Date.now() - 6_000).toISOString() },
        counts: { "sentiment_api:ingest": 892, "sentiment_api:summarize": 441, "sentiment_api:index": 112 }
      },
      daemon: {
        last_seen: new Date().toISOString(),
        age_sec: 4.1,
        last_cycle: { at: new Date(Date.now() - 55_000).toISOString(), sources: 42, queued: 18, interval_sec: 300 }
      }
    },
    redis: { status: "ok" },
    db: { status: "ok" }
  },
  backfill: {
    pushed: 324,
    sources: 42,
    from: new Date(Date.now() - 7 * 24 * 60 * 60_000).toISOString().slice(0, 10),
    to: new Date().toISOString().slice(0, 10)
  },
  logs: {
    api: [
      "2026-02-02 20:58:10 INFO sentiment_api.api Request complete 200 /v1/health",
      "2026-02-02 20:58:12 INFO sentiment_api.api Request complete 200 /v1/admin/ops"
    ],
    worker: [
      "2026-02-02 20:58:06 INFO sentiment_api.worker Worker started, synced 42 sources",
      "2026-02-02 20:58:08 INFO sentiment_api.worker Processed ingest -> summarize"
    ],
    daemon: [
      "2026-02-02 20:58:00 INFO sentiment_api.daemon Daemon started, polling 42 sources every 300s",
      "2026-02-02 20:58:03 INFO sentiment_api.daemon Poll cycle: 18 items queued"
    ]
  },
  mood: {
    as_of: new Date().toISOString(),
    sentiment: "RiskOff",
    trend: "Fading",
    index_intraday: -0.42,
    news_volume_intraday: 187,
    news_volatility_intraday: 0.73,
    confidence: 0.68,
    drivers: [],
    risk_vector: {
      risk_appetite: -0.62,
      volatility_pressure: 0.71,
      growth_outlook: -0.33,
      inflation_pressure: 0.22,
      rates_pressure: 0.41,
      liquidity_stress: 0.38,
      geopolitical_risk: 0.66,
      energy_supply_risk: 0.49
    }
  },
  intraday: Array.from({ length: 120 }).map((_, i) => {
    const ts = new Date(Date.now() - (119 - i) * 60_000).toISOString();
    const base = -0.25 + Math.sin(i / 10) * 0.18;
    return {
      ts,
      index_value: base + (Math.random() - 0.5) * 0.04,
      news_volume: Math.floor(10 + Math.random() * 30),
      news_volatility: Math.max(0, 0.25 + Math.sin(i / 17) * 0.2 + (Math.random() - 0.5) * 0.08),
      sentiment: base < -0.1 ? "RiskOff" : "Neutral"
    };
  }),
  markets: {
    as_of: new Date().toISOString(),
    methodology_version: "v2-demo",
    top_markets: [
      {
        market_id: "US_EQ",
        label_en: "US Equities",
        expected_direction: "RiskOff",
        magnitude: 0.72,
        confidence: 0.66,
        horizon: "1d",
        channels: ["geopolitics", "risk_appetite"],
        rationale_en: "Risk-off flow dominates; equity sensitivity elevated under geopolitical escalation."
      },
      {
        market_id: "USD",
        label_en: "US Dollar",
        expected_direction: "RiskOn",
        magnitude: 0.46,
        confidence: 0.58,
        horizon: "intraday",
        channels: ["risk_aversion"],
        rationale_en: "Safe-haven demand lifts USD short-term under uncertainty."
      },
      {
        market_id: "OIL",
        label_en: "Oil",
        expected_direction: "RiskOn",
        magnitude: 0.41,
        confidence: 0.55,
        horizon: "3d",
        channels: ["energy_supply"],
        rationale_en: "Supply-risk premium rises when shipping routes are threatened."
      }
    ]
  },
  sectors: {
    as_of: new Date().toISOString(),
    methodology_version: "v2-demo",
    sectors: [
      { sector_id: "GICS_10", sector_name_en: "Energy", expected_direction: "RiskOn", impact_score: 68, confidence: 0.61, horizon: "3d", channels: ["energy_supply"], rationale_en: "Supply shock benefits producers; volatility elevated." },
      { sector_id: "GICS_20", sector_name_en: "Industrials", expected_direction: "Neutral", impact_score: 41, confidence: 0.48, horizon: "1d", channels: ["supply_chain"], rationale_en: "Mixed: defense tailwind vs logistics headwinds." },
      { sector_id: "GICS_35", sector_name_en: "Health Care", expected_direction: "RiskOn", impact_score: 52, confidence: 0.50, horizon: "1d", channels: ["defensive"], rationale_en: "Defensive sector tends to outperform during risk-off regimes." },
      { sector_id: "GICS_45", sector_name_en: "Information Technology", expected_direction: "RiskOff", impact_score: 62, confidence: 0.60, horizon: "1d", channels: ["rates_pressure","risk_appetite"], rationale_en: "Long-duration growth pressured as rates and risk premium rise." },
      { sector_id: "GICS_40", sector_name_en: "Financials", expected_direction: "RiskOff", impact_score: 49, confidence: 0.44, horizon: "1d", channels: ["credit_stress"], rationale_en: "Risk-off widens credit spreads; lowers appetite for cyclicals." }
    ]
  },
  tickers: {
    as_of: new Date().toISOString(),
    methodology_version: "v2-demo",
    winners: [
      { symbol: "XOM", company_name_en: "Exxon Mobil", universe: "sp500", sector_id: "GICS_10", expected_direction: "RiskOn", expected_return_bps: 85, expected_volatility_delta: 0.7, confidence: 0.58, horizon: "3d", drivers: ["energy_supply"], rationale_en: "Supply-risk premium supports integrated majors." },
      { symbol: "LMT", company_name_en: "Lockheed Martin", universe: "sp500", sector_id: "GICS_20", expected_direction: "RiskOn", expected_return_bps: 62, expected_volatility_delta: 0.4, confidence: 0.55, horizon: "1w", drivers: ["defense_spend"], rationale_en: "Escalation increases defense budget expectations." },
      { symbol: "UNH", company_name_en: "UnitedHealth", universe: "sp500", sector_id: "GICS_35", expected_direction: "RiskOn", expected_return_bps: 38, expected_volatility_delta: 0.2, confidence: 0.50, horizon: "1d", drivers: ["defensive"], rationale_en: "Defensives hold up during risk-off sessions." }
    ],
    losers: [
      { symbol: "NVDA", company_name_en: "NVIDIA", universe: "nasdaq_composite", sector_id: "GICS_45", expected_direction: "RiskOff", expected_return_bps: -92, expected_volatility_delta: 1.1, confidence: 0.63, horizon: "1d", drivers: ["rates_pressure","risk_premium"], rationale_en: "High beta growth sells off when risk premium rises." },
      { symbol: "TSLA", company_name_en: "Tesla", universe: "nasdaq_composite", sector_id: "GICS_25", expected_direction: "RiskOff", expected_return_bps: -66, expected_volatility_delta: 0.9, confidence: 0.58, horizon: "1d", drivers: ["risk_premium"], rationale_en: "Risk-off de-risks high volatility names." },
      { symbol: "PLTR", company_name_en: "Palantir", universe: "nasdaq_composite", sector_id: "GICS_45", expected_direction: "RiskOff", expected_return_bps: -44, expected_volatility_delta: 0.6, confidence: 0.48, horizon: "1d", drivers: ["risk_premium"], rationale_en: "Momentum names are sensitive to macro uncertainty." }
    ]
  },
  topics: {
    as_of: new Date().toISOString(),
    points: Array.from({ length: 48 }).map((_, i) => {
      const ts = new Date(Date.now() - (47 - i) * 30 * 60_000).toISOString();
      return {
        ts,
        topic_id: i % 3 === 0 ? "GEOPOLITICS" : i % 3 === 1 ? "MACRO" : "RATES",
        topic_name_en: i % 3 === 0 ? "Geopolitics" : i % 3 === 1 ? "Macro" : "Rates",
        index_value: (i % 3 === 0 ? -1 : i % 3 === 1 ? -0.4 : -0.2) * (0.6 + Math.sin(i / 7) * 0.2),
        sentiment: i % 3 === 0 ? "RiskOff" : "Neutral",
        news_volume: Math.floor(20 + Math.random() * 50)
      };
    })
  },
  clusters: [
    {
      cluster_id: "clu_demo_001",
      first_seen: new Date(Date.now() - 2 * 60 * 60_000).toISOString(),
      last_seen: new Date(Date.now() - 30 * 60_000).toISOString(),
      headline_en: "Tensions escalate near key shipping corridor",
      summary_bullets_en: [
        "Regional military activity increases; shipping insurers raise premiums.",
        "Oil supply disruption risk rises; safe-haven flows pick up.",
        "Equities trade risk-off; volatility elevated intraday."
      ],
      topics: ["geopolitics", "energy"],
      regions: ["GLOBAL"],
      source_count: 6,
      source_urls: ["https://example.com/a", "https://example.com/b"],
      impact: { impact_score: 78, impact_level: "L4", expected_direction: "RiskOff", horizon: "1d", confidence: 0.66, reason_codes: ["WAR_ESCALATION","ENERGY_SUPPLY_RISK"] },
      top_markets: [],
      top_sectors: [],
      top_tickers_winners: [],
      top_tickers_losers: []
    },
    {
      cluster_id: "clu_demo_002",
      first_seen: new Date(Date.now() - 6 * 60 * 60_000).toISOString(),
      last_seen: new Date(Date.now() - 4 * 60 * 60_000).toISOString(),
      headline_en: "Central bank signals slower pace of tightening",
      summary_bullets_en: [
        "Officials hint at potential pause if inflation eases.",
        "Rates fall; duration-sensitive equities stabilize."
      ],
      topics: ["rates", "macro"],
      regions: ["US"],
      source_count: 4,
      source_urls: ["https://example.com/c"],
      impact: { impact_score: 61, impact_level: "L3", expected_direction: "RiskOn", horizon: "3d", confidence: 0.58, reason_codes: ["RATES_DOVISH"] },
      top_markets: [],
      top_sectors: [],
      top_tickers_winners: [],
      top_tickers_losers: []
    }
  ]
};
