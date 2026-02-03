import { z } from "zod";
import { unwrapEnvelope } from "./contracts";
import { demo } from "../demo/data";

function getApiBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";
  if (typeof window === "undefined") return configured;
  // When page is on a non-localhost host but API is configured as localhost, use same host (fixes CORS/loopback when accessing by IP)
  const isLocalhost = /^localhost$|^127\.\d+\.\d+\.\d+$/.test(window.location.hostname);
  const apiIsLocalhost = /^https?:\/\/(localhost|127\.\d+\.\d+\.\d+)(:\d+)?(\/|$)/.test(configured);
  if (!isLocalhost && apiIsLocalhost) {
    return `${window.location.protocol}//${window.location.hostname}:8080`;
  }
  return configured;
}

export const API_BASE = getApiBase();

function getDemoMode(): boolean {
  if (process.env.NEXT_PUBLIC_DEMO_MODE === "1") return true;
  if (typeof window === "undefined") return false;
  return localStorage.getItem("SENTIMETER_DEMO_MODE") === "1";
}

function getApiKey(): string | undefined {
  if (typeof window === "undefined") return undefined;
  const k = localStorage.getItem("SENTIMETER_API_KEY") || "";
  return k.trim() || undefined;
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export class ApiError extends Error {
  status: number;
  code?: string;
  requestId?: string;
  retryable?: boolean;
  constructor(msg: string, status: number, code?: string, requestId?: string, retryable?: boolean) {
    super(msg);
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.retryable = retryable;
  }
}

type FetchOpts = {
  apiKey?: string;
  retry?: boolean;
  signal?: AbortSignal;
};

export async function apiGetData<T>(
  path: string,
  dataSchema: z.ZodTypeAny,
  opts: FetchOpts = {}
): Promise<{ data: T; meta?: any; errors?: any[]; degraded?: boolean }> {
  if (getDemoMode()) {
    // Demo mode: map endpoints to demo payloads.
    const d: any = demo;
    if (path.startsWith("/v1/health")) return { data: dataSchema.parse(d.health) };
    if (path.startsWith("/v1/status")) return { data: dataSchema.parse(d.status) };
    if (path.startsWith("/v1/admin/ops")) return { data: dataSchema.parse(d.ops) };
    if (path.startsWith("/v1/admin/logs")) return { data: dataSchema.parse(d.logs) };
    if (path.startsWith("/v1/mood/now")) return { data: dataSchema.parse(d.mood) };
    if (path.startsWith("/v1/index/intraday")) return { data: dataSchema.parse(d.intraday) };
    if (path.startsWith("/v1/impacts/latest")) return { data: dataSchema.parse(d.impacts) };
    if (path.startsWith("/v1/impact/markets")) return { data: dataSchema.parse(d.markets) };
    if (path.startsWith("/v1/impact/sectors")) return { data: dataSchema.parse(d.sectors) };
    if (path.startsWith("/v1/impact/tickers")) return { data: dataSchema.parse(d.tickers) };
    if (path.startsWith("/v1/topics/index")) return { data: dataSchema.parse(d.topics) };
    if (path.startsWith("/v1/news/clusters/") && !path.endsWith("/impacts")) {
      const id = path.split("/v1/news/clusters/")[1].split("?")[0];
      const clu = d.clusters.find((x: any) => x.cluster_id === id) || d.clusters[0];
      const detail = { cluster: clu, evidence: [{ url: "https://example.com/a", text_en: "Demo evidence passage.", relevance_score: 0.9 }], articles: [] };
      return { data: dataSchema.parse(detail) };
    }
    if (path.startsWith("/v1/news/clusters")) return { data: dataSchema.parse(d.clusters) };
    if (path.startsWith("/v1/sources")) return { data: dataSchema.parse({ sources: [] }) };
    return { data: dataSchema.parse({}) };
  }

  const apiKey = opts.apiKey ?? getApiKey();
  const url = new URL(path, API_BASE);
  if (apiKey) url.searchParams.set("api_key", apiKey);

  const doFetch = async (): Promise<{ data: T; meta?: any; errors?: any[]; degraded?: boolean }> => {
    const res = await fetch(url.toString(), { cache: "no-store", signal: opts.signal });
    const text = await res.text();

    if (!res.ok) {
      let code: string | undefined;
      let requestId: string | undefined;
      let retryable: boolean | undefined;
      try {
        const parsed = JSON.parse(text);
        code = parsed?.errors?.[0]?.code;
        requestId = parsed?.meta?.request_id;
        retryable = parsed?.errors?.[0]?.retryable;
      } catch {}

      if (res.status === 429) {
        const retryAfter = Number(res.headers.get("Retry-After") || "1");
        if (opts.retry !== false) {
          await sleep(Math.min(Math.max(retryAfter, 1), 10) * 1000);
          return doFetch();
        }
      }

      throw new ApiError(`API ${res.status}${code ? ` ${code}` : ""}`, res.status, code, requestId, retryable);
    }

    const json = JSON.parse(text);
    const unwrapped = unwrapEnvelope(json);
    const parsed = dataSchema.safeParse(unwrapped.data);
    if (!parsed.success) {
      // Degraded mode: schema mismatch; allow UI to show fallback.
      return { data: unwrapped.data as T, meta: unwrapped.meta, errors: unwrapped.errors, degraded: true };
    }
    return { data: parsed.data as T, meta: unwrapped.meta, errors: unwrapped.errors };
  };

  return doFetch();
}

export async function apiPostData<T>(
  path: string,
  body: any,
  dataSchema: z.ZodTypeAny,
  opts: FetchOpts = {}
): Promise<{ data: T; meta?: any; errors?: any[]; degraded?: boolean }> {
  if (getDemoMode()) {
    const d: any = demo;
    if (path.startsWith("/v1/admin/backfill")) return { data: dataSchema.parse(d.backfill) };
    if (path.startsWith("/v1/admin/ingest/run")) return { data: dataSchema.parse({ pushed: 0, sources_polled: 0 }) };
    if (path.startsWith("/v1/admin/summarize/run")) return { data: dataSchema.parse({ queued: 0 }) };
    if (path.startsWith("/v1/admin/scale/workers")) return { data: dataSchema.parse({ count: body?.count ?? 0, applied: false, message: "Demo mode: scale not applied." }) };
    return { data: dataSchema.parse({}) };
  }

  const apiKey = opts.apiKey ?? getApiKey();
  const url = new URL(path, API_BASE);
  if (apiKey) url.searchParams.set("api_key", apiKey);

  const doFetch = async (): Promise<{ data: T; meta?: any; errors?: any[]; degraded?: boolean }> => {
    const res = await fetch(url.toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body ?? {}),
      cache: "no-store",
      signal: opts.signal
    });
    const text = await res.text();

    if (!res.ok) {
      let code: string | undefined;
      let requestId: string | undefined;
      let retryable: boolean | undefined;
      try {
        const parsed = JSON.parse(text);
        code = parsed?.errors?.[0]?.code;
        requestId = parsed?.meta?.request_id;
        retryable = parsed?.errors?.[0]?.retryable;
      } catch {}

      if (res.status === 429) {
        const retryAfter = Number(res.headers.get("Retry-After") || "1");
        if (opts.retry !== false) {
          await sleep(Math.min(Math.max(retryAfter, 1), 10) * 1000);
          return doFetch();
        }
      }

      throw new ApiError(`API ${res.status}${code ? ` ${code}` : ""}`, res.status, code, requestId, retryable);
    }

    const json = JSON.parse(text);
    const unwrapped = unwrapEnvelope(json);
    const parsed = dataSchema.safeParse(unwrapped.data);
    if (!parsed.success) {
      return { data: unwrapped.data as T, meta: unwrapped.meta, errors: unwrapped.errors, degraded: true };
    }
    return { data: parsed.data as T, meta: unwrapped.meta, errors: unwrapped.errors };
  };

  return doFetch();
}
