"use client";

import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { apiGetData } from "./client";
import {
  HealthData,
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

export function useImpactMarkets() {
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
    refetchInterval: 30_000
  });
}

export function useImpactSectors() {
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
    refetchInterval: 30_000
  });
}

export function useImpactTickers() {
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
    refetchInterval: 30_000
  });
}

export function useTopicsIndex() {
  return useQuery<z.infer<typeof TopicsIndexData>>({
    queryKey: ["topicsIndex"],
    queryFn: async () => {
      const res = await apiGetData("/v1/topics/index?interval=15m", z.array(TopicPoint));
      return {
        as_of: new Date().toISOString(),
        points: res.data as Array<z.infer<typeof TopicPoint>>
      };
    },
    refetchInterval: 30_000
  });
}

export function useClusters() {
  return useQuery<Array<z.infer<typeof ClusterSummary>>>({
    queryKey: ["clusters"],
    queryFn: async () => {
      const res = await apiGetData("/v1/news/clusters?min_impact_level=L2&limit=50", z.array(ClusterSummary));
      return res.data as Array<z.infer<typeof ClusterSummary>>;
    },
    refetchInterval: 30_000
  });
}

export function useClusterDetail(clusterId: string) {
  return useQuery<z.infer<typeof ClusterDetail>>({
    queryKey: ["clusterDetail", clusterId],
    queryFn: async () => {
      const res = await apiGetData(`/v1/news/clusters/${clusterId}?include_articles=true&include_evidence=true`, ClusterDetail);
      return res.data as z.infer<typeof ClusterDetail>;
    }
  });
}

export function useSources() {
  return useQuery<z.infer<typeof SourcesData>>({
    queryKey: ["sources"],
    queryFn: async () => {
      const res = await apiGetData("/v1/sources", SourcesData);
      return res.data as z.infer<typeof SourcesData>;
    },
    refetchInterval: 60_000
  });
}
