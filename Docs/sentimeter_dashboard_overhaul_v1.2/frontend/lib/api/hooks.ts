"use client";

import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { apiGet } from "./client";
import {
  ApiEnvelope,
  MoodSnapshot,
  IntradayIndexPoint,
  ClusterSummary,
  ClusterDetail,
  ImpactMarketsResponse,
  ImpactSectorsResponse,
  ImpactTickersResponse,
  TopicsIndexResponse,
  SourcesResponse,
  HealthResponse,
} from "./contracts";

const API_KEYLESS = undefined;

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet("/v1/health", ApiEnvelope(HealthResponse), { apiKey: API_KEYLESS }),
    refetchInterval: 10_000,
  });
}

export function useMoodNow() {
  return useQuery({
    queryKey: ["moodNow"],
    queryFn: () => apiGet("/v1/mood/now", ApiEnvelope(MoodSnapshot), {}),
    refetchInterval: 10_000,
  });
}

export function useIntradayIndex() {
  return useQuery({
    queryKey: ["intradayIndex"],
    queryFn: () => apiGet("/v1/index/intraday?interval=5m&limit=200", ApiEnvelope(z.array(IntradayIndexPoint)), {}),
    refetchInterval: 10_000,
  });
}

export function useClusters() {
  return useQuery({
    queryKey: ["clusters"],
    queryFn: () => apiGet("/v1/news/clusters?min_impact_level=L2&limit=50", ApiEnvelope(z.array(ClusterSummary)), {}),
    refetchInterval: 30_000,
  });
}

export function useClusterDetail(clusterId: string) {
  return useQuery({
    queryKey: ["clusterDetail", clusterId],
    queryFn: () => apiGet(`/v1/news/clusters/${clusterId}?include_articles=true&include_evidence=true`, ApiEnvelope(ClusterDetail), {}),
  });
}

export function useImpactMarkets() {
  return useQuery({
    queryKey: ["impactMarkets"],
    queryFn: () => apiGet("/v1/impact/markets", ApiEnvelope(ImpactMarketsResponse), {}),
    refetchInterval: 30_000,
  });
}

export function useImpactSectors() {
  return useQuery({
    queryKey: ["impactSectors"],
    queryFn: () => apiGet("/v1/impact/sectors", ApiEnvelope(ImpactSectorsResponse), {}),
    refetchInterval: 30_000,
  });
}

export function useImpactTickers() {
  return useQuery({
    queryKey: ["impactTickers"],
    queryFn: () => apiGet("/v1/impact/tickers", ApiEnvelope(ImpactTickersResponse), {}),
    refetchInterval: 30_000,
  });
}

export function useTopicsIndex() {
  return useQuery({
    queryKey: ["topicsIndex"],
    queryFn: () => apiGet("/v1/topics/index?interval=15m", ApiEnvelope(TopicsIndexResponse), {}),
    refetchInterval: 30_000,
  });
}

export function useSources() {
  return useQuery({
    queryKey: ["sources"],
    queryFn: () => apiGet("/v1/sources", ApiEnvelope(SourcesResponse), {}),
    refetchInterval: 60_000,
  });
}
