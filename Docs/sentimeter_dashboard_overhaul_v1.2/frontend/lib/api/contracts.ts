import { z } from "zod";

export const Direction = z.enum(["RiskOn","RiskOff","Neutral","Mixed","Unknown"]);
export const ImpactLevel = z.enum(["L0","L1","L2","L3","L4","L5"]);
export const Horizon = z.enum(["intraday","1d","3d","1w","1m","unknown"]);

export const ErrorItem = z.object({
  code: z.string().min(1),
  message: z.string().min(1),
  details: z.record(z.any()).default({}),
  hint: z.string().optional().nullable(),
  retryable: z.boolean().optional().default(false),
});

export const ResponseMeta = z.object({
  request_id: z.string().min(8),
  as_of: z.string(),
  trace_id: z.string().optional().nullable(),
  model_versions: z.record(z.string()).optional().default({}),
});

export const ApiEnvelope = <T extends z.ZodTypeAny>(data: T) =>
  z.object({
    meta: ResponseMeta,
    data,
    errors: z.array(ErrorItem).default([]),
  });

export const Pagination = z.object({
  limit: z.number().int().min(1).max(500),
  next_cursor: z.string().optional().nullable(),
  returned: z.number().int().min(0),
});

export const ApiListEnvelope = <T extends z.ZodTypeAny>(item: T) =>
  z.object({
    meta: ResponseMeta,
    pagination: Pagination,
    data: z.array(item),
    errors: z.array(ErrorItem).default([]),
  });

export const MoodSnapshot = z.object({
  as_of: z.string(),
  sentiment: Direction,
  trend: z.string(),
  index_intraday: z.number(),
  news_volume_intraday: z.number().int().min(0),
  news_volatility_intraday: z.number().min(0),
  confidence: z.number().min(0).max(1),
  drivers: z.array(z.any()).default([]),
  risk_vector: z.record(z.any()).default({}),
});

export const IntradayIndexPoint = z.object({
  ts: z.string(),
  index_value: z.number(),
  news_volume: z.number().int().min(0),
  news_volatility: z.number().min(0),
  sentiment: Direction,
});

export const ClusterImpact = z.object({
  impact_score: z.number().min(0).max(100),
  impact_level: ImpactLevel,
  expected_direction: Direction,
  horizon: Horizon,
  confidence: z.number().min(0).max(1),
  reason_codes: z.array(z.string()).default([]),
});

export const TickerImpact = z.object({
  symbol: z.string().min(1).max(16),
  company_name_en: z.string().optional().nullable(),
  universe: z.string(),
  sector_id: z.string().optional().nullable(),
  expected_direction: Direction,
  expected_return_bps: z.number().min(-5000).max(5000),
  expected_volatility_delta: z.number().min(-5).max(5),
  confidence: z.number().min(0).max(1),
  horizon: Horizon,
  drivers: z.array(z.string()).default([]),
  rationale_en: z.string().min(10),
});

export const SectorImpact = z.object({
  sector_id: z.string(),
  sector_name_en: z.string(),
  expected_direction: Direction,
  impact_score: z.number().min(0).max(100),
  confidence: z.number().min(0).max(1),
  horizon: Horizon,
  channels: z.array(z.string()).default([]),
  rationale_en: z.string().min(10),
});

export const MarketImpact = z.object({
  market_id: z.string(),
  label_en: z.string(),
  expected_direction: Direction,
  magnitude: z.number().min(0).max(1),
  confidence: z.number().min(0).max(1),
  horizon: Horizon,
  channels: z.array(z.string()).default([]),
  rationale_en: z.string().min(10),
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
  top_tickers_losers: z.array(TickerImpact).default([]),
});

export const EvidencePassage = z.object({
  url: z.string(),
  text_en: z.string().min(1),
  relevance_score: z.number().min(0).max(1),
});

export const ArticleRef = z.object({
  article_id: z.string(),
  source_id: z.string(),
  url: z.string(),
  published_at: z.string(),
  title_en: z.string(),
  lang_original: z.string(),
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
  ticker_impacts: z.array(TickerImpact).optional().default([]),
});

export const SourcesItem = z.object({
  source_id: z.string(),
  name: z.string(),
  type: z.string(),
  credibility_tier: z.string(),
  license_class: z.string(),
  enabled: z.boolean().optional().default(true),
});

export const SourcesResponse = z.object({ sources: z.array(SourcesItem) });

export const ImpactMarketsResponse = z.object({
  as_of: z.string(),
  top_markets: z.array(MarketImpact).min(1),
  methodology_version: z.string(),
});

export const ImpactSectorsResponse = z.object({
  as_of: z.string(),
  sectors: z.array(SectorImpact).min(1),
  methodology_version: z.string(),
});

export const ImpactTickersResponse = z.object({
  as_of: z.string(),
  winners: z.array(TickerImpact),
  losers: z.array(TickerImpact),
  methodology_version: z.string(),
});

export const TopicsIndexPoint = z.object({
  ts: z.string(),
  topic_id: z.string(),
  topic_name_en: z.string(),
  index_value: z.number(),
  sentiment: Direction,
  news_volume: z.number().int().min(0),
});

export const TopicsIndexResponse = z.object({
  as_of: z.string(),
  points: z.array(TopicsIndexPoint),
});

export const HealthResponse = z.object({
  status: z.enum(["ok","degraded","down"]),
  as_of: z.string(),
  checks: z.array(z.any()).default([]),
});
