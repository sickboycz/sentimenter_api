"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { z } from "zod";
import { apiGetData, apiPostData } from "./client";
import {
  HealthData,
  StatusData,
  OpsStatus,
  LogsData,
  BackfillResult,
  IngestRunResult,
  SummarizeRunResult,
  MoodNowData,
  IntradayPoint,
  MarketImpact,
  MarketImpactSummary,
  SectorImpact,
  SectorImpactSummary,
  TickerImpact,
  TickerImpactSummary,
  TopicPoint,
  TopicsIndexData,
  ClusterSummary,
  ClusterDetail,
  SourcesData
} from "./contracts";

export function useHealth() {
  return useQuery<z.infer<typeof HealthData>>({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await apiGetData("/v1/health", HealthData);
      return res.data as z.infer<typeof HealthData>;
    },
    refetchInterval: 10_000
  });
}

export function useStatus() {
  return useQuery<z.infer<typeof StatusData>>({
    queryKey: ["status"],
    queryFn: async () => {
      const res = await apiGetData("/v1/status", StatusData);
      return res.data as z.infer<typeof StatusData>;
    },
    refetchInterval: 10_000
  });
}

export function useOpsStatus(enabled: boolean = true) {
  return useQuery<z.infer<typeof OpsStatus>>({
    queryKey: ["opsStatus"],
    queryFn: async () => {
      const res = await apiGetData("/v1/admin/ops", OpsStatus);
      return res.data as z.infer<typeof OpsStatus>;
    },
    refetchInterval: 5_000,
    enabled
  });
}

export function useAdminLogs() {
  return useQuery<z.infer<typeof LogsData>>({
    queryKey: ["adminLogs"],
    queryFn: async () => {
      const res = await apiGetData("/v1/admin/logs?tail=200&sources=api&sources=worker&sources=daemon", LogsData);
      return res.data as z.infer<typeof LogsData>;
    },
    refetchInterval: 10_000
  });
}

export function useAdminBackfill() {
  return useMutation({
    mutationFn: async (payload: { from: string; to: string }) => {
      const res = await apiPostData("/v1/admin/backfill", payload, BackfillResult);
      return res.data as z.infer<typeof BackfillResult>;
    }
  });
}

export function useAdminIngestRun() {
  return useMutation({
    mutationFn: async (sourceId?: string) => {
      const url = sourceId ? `/v1/admin/ingest/run?source_id=${encodeURIComponent(sourceId)}` : "/v1/admin/ingest/run";
      const res = await apiPostData(url, {}, IngestRunResult);
      return res.data as z.infer<typeof IngestRunResult>;
    }
  });
}

export function useAdminSummarizeRun() {
  return useMutation({
    mutationFn: async (params?: { limit?: number; dryRun?: boolean }) => {
      const sp = new URLSearchParams();
      if (params?.limit != null) sp.set("limit", String(params.limit));
      if (params?.dryRun) sp.set("dry_run", "1");
      const q = sp.toString() ? `?${sp}` : "";
      const res = await apiPostData(`/v1/admin/summarize/run${q}`, {}, SummarizeRunResult);
      return res.data as z.infer<typeof SummarizeRunResult>;
    }
  });
}

export function useMoodNow() {
  return useQuery<z.infer<typeof MoodNowData>>({
    queryKey: ["moodNow"],
    queryFn: async () => {
      const res = await apiGetData("/v1/mood/now", MoodNowData);
      return res.data as z.infer<typeof MoodNowData>;
    },
    refetchInterval: 10_000
  });
}

export function useIntradayIndex() {
  return useQuery<Array<z.infer<typeof IntradayPoint>>>({
    queryKey: ["intradayIndex"],
    queryFn: async () => {
      const res = await apiGetData("/v1/index/intraday?interval=1m&limit=500", z.array(IntradayPoint));
      return res.data as Array<z.infer<typeof IntradayPoint>>;
    },
    refetchInterval: 10_000
  });
}

const ImpactsLatestBundle = z.object({
  as_of: z.string(),
  scope: z.any(),
  most_affected_market: z.any().optional(),
  markets: z.array(MarketImpact).default([]),
  sectors: z.array(SectorImpact).default([]),
  winners: z.array(TickerImpact).default([]),
  losers: z.array(TickerImpact).default([]),
  notes_en: z.string().optional()
});

export function useImpactMarkets(enabled: boolean = true) {
  return useQuery<z.infer<typeof MarketImpactSummary>>({
    queryKey: ["impactMarkets"],
    queryFn: async () => {
      const res = await apiGetData("/v1/impacts/latest?window=6h&limit_tickers=0&limit_sectors=0", ImpactsLatestBundle);
      const bundle = res.data as z.infer<typeof ImpactsLatestBundle>;
      return {
        as_of: bundle.as_of,
        top_markets: bundle.markets || [],
        methodology_version: "v1.2"
      } as z.infer<typeof MarketImpactSummary>;
    },
    refetchInterval: 30_000,
    enabled
  });
}

export function useImpactSectors(enabled: boolean = true) {
  return useQuery<z.infer<typeof SectorImpactSummary>>({
    queryKey: ["impactSectors"],
    queryFn: async () => {
      const res = await apiGetData("/v1/impacts/latest?window=6h&limit_tickers=0&limit_sectors=11", ImpactsLatestBundle);
      const bundle = res.data as z.infer<typeof ImpactsLatestBundle>;
      return {
        as_of: bundle.as_of,
        sectors: bundle.sectors || [],
        methodology_version: "v1.2"
      } as z.infer<typeof SectorImpactSummary>;
    },
    refetchInterval: 30_000,
    enabled
  });
}

export function useImpactTickers(enabled: boolean = true) {
  return useQuery<z.infer<typeof TickerImpactSummary>>({
    queryKey: ["impactTickers"],
    queryFn: async () => {
      const res = await apiGetData("/v1/impacts/latest?window=6h&limit_tickers=100&limit_sectors=0", ImpactsLatestBundle);
      const bundle = res.data as z.infer<typeof ImpactsLatestBundle>;
      return {
        as_of: bundle.as_of,
        winners: bundle.winners || [],
        losers: bundle.losers || [],
        methodology_version: "v1.2"
      } as z.infer<typeof TickerImpactSummary>;
    },
    refetchInterval: 30_000,
    enabled
  });
}

export function useTopicsIndex(enabled: boolean = true) {
  return useQuery<z.infer<typeof TopicsIndexData>>({
    queryKey: ["topicsIndex"],
    queryFn: async () => {
      const res = await apiGetData("/v1/topics/index?interval=15m", z.array(TopicPoint));
      return {
        as_of: new Date().toISOString(),
        points: res.data as Array<z.infer<typeof TopicPoint>>
      };
    },
    refetchInterval: 30_000,
    enabled
  });
}

export function useClusters(enabled: boolean = true) {
  return useQuery<Array<z.infer<typeof ClusterSummary>>>({
    queryKey: ["clusters"],
    queryFn: async () => {
      const res = await apiGetData("/v1/news/clusters?min_impact_level=L2&limit=50", z.array(ClusterSummary));
      return res.data as Array<z.infer<typeof ClusterSummary>>;
    },
    refetchInterval: 30_000,
    enabled
  });
}

export function useClusterDetail(clusterId: string, enabled: boolean = true) {
  return useQuery<z.infer<typeof ClusterDetail>>({
    queryKey: ["clusterDetail", clusterId],
    queryFn: async () => {
      const res = await apiGetData(`/v1/news/clusters/${clusterId}?include_articles=true&include_evidence=true`, ClusterDetail);
      return res.data as z.infer<typeof ClusterDetail>;
    },
    enabled
  });
}

export function useSources(enabled: boolean = true) {
  return useQuery<z.infer<typeof SourcesData>>({
    queryKey: ["sources"],
    queryFn: async () => {
      const res = await apiGetData("/v1/sources", SourcesData);
      return res.data as z.infer<typeof SourcesData>;
    },
    refetchInterval: 60_000,
    enabled
  });
}
