import { z } from "zod";

export const Direction = z.enum(["RiskOn","RiskOff","Neutral","Mixed","Unknown"]);
export const ImpactLevel = z.enum(["L0","L1","L2","L3","L4","L5"]);
export const Horizon = z.enum(["intraday","1d","3d","1w","1m","unknown"]);

export const HealthData = z.object({
  status: z.enum(["ok","degraded","down"]),
  as_of: z.string(),
  checks: z.array(z.any()).default([])
});

export const SourceItem = z.object({
  source_id: z.string(),
  name: z.string(),
  type: z.string(),
  credibility_tier: z.string(),
  license_class: z.string(),
  enabled: z.boolean().optional().default(true)
});
export const SourcesData = z.object({ sources: z.array(SourceItem) });

export const MoodNowData = z.object({
  as_of: z.string(),
  sentiment: Direction,
  trend: z.string(),
  index_intraday: z.number(),
  news_volume_intraday: z.number().int().min(0),
  news_volatility_intraday: z.number().min(0),
  confidence: z.number().min(0).max(1),
  drivers: z.array(z.any()).default([]),
  risk_vector: z.record(z.any()).default({})
});

export const IntradayPoint = z.object({
  ts: z.string(),
  index_value: z.number(),
  news_volume: z.number().int().min(0),
  news_volatility: z.number().min(0),
  sentiment: Direction
});

export const MarketImpact = z.object({
  market_id: z.string(),
  label_en: z.string(),
  direction: Direction,
  impact_score: z.number().min(0).max(100),
  confidence: z.number().min(0).max(1),
  horizon: Horizon,
  channels: z.array(z.string()).default([]),
  rationale_bullets_en: z.array(z.string()).default([])
});
export const MarketImpactSummary = z.object({
  as_of: z.string(),
  top_markets: z.array(MarketImpact),
  methodology_version: z.string()
});

export const SectorImpact = z.object({
  sector_id: z.string(),
  sector_name_en: z.string(),
  direction: Direction,
  impact_score: z.number().min(0).max(100),
  confidence: z.number().min(0).max(1),
  horizon: Horizon,
  channels: z.array(z.string()).default([]),
  rationale_bullets_en: z.array(z.string()).default([])
});
export const SectorImpactSummary = z.object({
  as_of: z.string(),
  sectors: z.array(SectorImpact),
  methodology_version: z.string()
});

export const TickerImpact = z.object({
  symbol: z.string().min(1).max(16),
  name: z.string().optional().nullable(),
  universe_memberships: z.array(z.string()).default([]),
  sector_id: z.string().optional().nullable(),
  sector_name_en: z.string().optional().nullable(),
  direction: Direction,
  impact_score: z.number().min(0).max(100),
  confidence: z.number().min(0).max(1),
  horizon: Horizon,
  channels: z.array(z.string()).default([]),
  rationale_bullets_en: z.array(z.string()).default([]),
  driver_clusters: z.array(z.string()).default([]),
  evidence_urls: z.array(z.string()).default([]),
  historical_edge: z.array(z.any()).default([])
});
export const TickerImpactSummary = z.object({
  as_of: z.string(),
  winners: z.array(TickerImpact),
  losers: z.array(TickerImpact),
  methodology_version: z.string()
});

export const TopicPoint = z.object({
  ts: z.string(),
  topic_id: z.string(),
  topic_name_en: z.string(),
  index_value: z.number(),
  sentiment: Direction,
  news_volume: z.number().int().min(0)
});
export const TopicsIndexData = z.object({
  as_of: z.string(),
  points: z.array(TopicPoint)
});

export const ClusterImpact = z.object({
  impact_score: z.number().min(0).max(100),
  impact_level: ImpactLevel,
  expected_direction: Direction,
  horizon: Horizon,
  confidence: z.number().min(0).max(1),
  reason_codes: z.array(z.string()).default([])
});

export const ClusterSummary = z.object({
  cluster_id: z.string(),
  first_seen: z.string(),
  last_seen: z.string(),
  headline_en: z.string(),
  summary_bullets_en: z.array(z.string()).min(1).max(12),
  topics: z.array(z.string()).default([]),
  regions: z.array(z.string()).default([]),
  source_count: z.number().int().min(1),
  source_urls: z.array(z.string()).default([]),
  impact: ClusterImpact,

  top_markets: z.array(MarketImpact).default([]),
  top_sectors: z.array(SectorImpact).default([]),
  top_tickers_winners: z.array(TickerImpact).default([]),
  top_tickers_losers: z.array(TickerImpact).default([])
});

export const EvidencePassage = z.object({
  url: z.string(),
  text_en: z.string(),
  relevance_score: z.number().min(0).max(1)
});

export const ArticleRef = z.object({
  article_id: z.string(),
  source_id: z.string(),
  url: z.string(),
  published_at: z.string(),
  title_en: z.string(),
  lang_original: z.string()
});

export const ClusterDetail = z.object({
  cluster: ClusterSummary,
  articles: z.array(ArticleRef).default([]),
  evidence: z.array(EvidencePassage).default([]),
  what_changed_en: z.string().optional().nullable(),
  why_it_matters_en: z.string().optional().nullable(),
  what_to_watch_en: z.string().optional().nullable(),
  impact_explanation_en: z.string().optional().nullable(),

  market_impacts: z.array(MarketImpact).optional().default([]),
  sector_impacts: z.array(SectorImpact).optional().default([]),
  ticker_impacts: z.array(TickerImpact).optional().default([])
});

export function unwrapEnvelope(json: any): { data: any; meta?: any; errors?: any[] } {
  if (json && typeof json === "object" && "data" in json && "meta" in json) {
    return { data: json.data, meta: json.meta, errors: json.errors || [] };
  }
  return { data: json, meta: undefined, errors: [] };
}
