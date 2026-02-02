"use client";

import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { apiGetData } from "./client";
import {
  HealthData,
  MoodNowData,
  IntradayPoint,
  MarketImpactSummary,
  SectorImpactSummary,
  TickerImpactSummary,
  TopicsIndexData,
  ClusterSummary,
  ClusterDetail,
  SourcesData
} from "./contracts";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiGetData("/v1/health", HealthData),
    refetchInterval: 10_000
  });
}

export function useMoodNow() {
  return useQuery({
    queryKey: ["moodNow"],
    queryFn: () => apiGetData("/v1/mood/now", MoodNowData),
    refetchInterval: 10_000
  });
}

export function useIntradayIndex() {
  return useQuery({
    queryKey: ["intradayIndex"],
    queryFn: () => apiGetData("/v1/index/intraday?interval=1m&limit=500", z.array(IntradayPoint)),
    refetchInterval: 10_000
  });
}

export function useImpactMarkets() {
  return useQuery({
    queryKey: ["impactMarkets"],
    queryFn: () => apiGetData("/v1/impact/markets", MarketImpactSummary),
    refetchInterval: 30_000
  });
}

export function useImpactSectors() {
  return useQuery({
    queryKey: ["impactSectors"],
    queryFn: () => apiGetData("/v1/impact/sectors", SectorImpactSummary),
    refetchInterval: 30_000
  });
}

export function useImpactTickers() {
  return useQuery({
    queryKey: ["impactTickers"],
    queryFn: () => apiGetData("/v1/impact/tickers", TickerImpactSummary),
    refetchInterval: 30_000
  });
}

export function useTopicsIndex() {
  return useQuery({
    queryKey: ["topicsIndex"],
    queryFn: () => apiGetData("/v1/topics/index?interval=15m", TopicsIndexData),
    refetchInterval: 30_000
  });
}

export function useClusters() {
  return useQuery({
    queryKey: ["clusters"],
    queryFn: () => apiGetData("/v1/news/clusters?min_impact_level=L2&limit=50", z.array(ClusterSummary)),
    refetchInterval: 30_000
  });
}

export function useClusterDetail(clusterId: string) {
  return useQuery({
    queryKey: ["clusterDetail", clusterId],
    queryFn: () => apiGetData(`/v1/news/clusters/${clusterId}?include_articles=true&include_evidence=true`, ClusterDetail)
  });
}

export function useSources() {
  return useQuery({
    queryKey: ["sources"],
    queryFn: () => apiGetData("/v1/sources", SourcesData),
    refetchInterval: 60_000
  });
}
