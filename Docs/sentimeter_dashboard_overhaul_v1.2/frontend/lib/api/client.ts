import { z } from "zod";

type FetchOpts = {
  apiKey?: string;
  signal?: AbortSignal;
  retry?: boolean;
};

function getApiKey(): string | undefined {
  if (typeof window === "undefined") return undefined;
  return localStorage.getItem("SENTIMETER_API_KEY") || undefined;
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export class ApiError extends Error {
  status: number;
  requestId?: string;
  code?: string;
  retryable?: boolean;
  constructor(message: string, status: number, requestId?: string, code?: string, retryable?: boolean) {
    super(message);
    this.status = status;
    this.requestId = requestId;
    this.code = code;
    this.retryable = retryable;
  }
}

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function apiGet<T>(
  path: string,
  schema: z.ZodTypeAny,
  opts: FetchOpts = {}
): Promise<T> {
  const apiKey = opts.apiKey ?? getApiKey();
  const url = new URL(path, API_BASE);

  if (apiKey) url.searchParams.set("api_key", apiKey);

  const doFetch = async (): Promise<T> => {
    const res = await fetch(url.toString(), { cache: "no-store", signal: opts.signal });
    const text = await res.text();

    if (!res.ok) {
      let requestId: string | undefined;
      let code: string | undefined;
      let retryable: boolean | undefined;

      try {
        const parsed = JSON.parse(text);
        requestId = parsed?.meta?.request_id;
        code = parsed?.errors?.[0]?.code;
        retryable = parsed?.errors?.[0]?.retryable;
      } catch {}

      if (res.status === 429) {
        const retryAfter = Number(res.headers.get("Retry-After") || "1");
        if (opts.retry !== false) {
          await sleep(Math.min(Math.max(retryAfter, 1), 10) * 1000);
          return doFetch();
        }
      }

      throw new ApiError(`API ${res.status} ${code || ""}`.trim(), res.status, requestId, code, retryable);
    }

    const json = JSON.parse(text);
    const parsed = schema.safeParse(json);
    if (!parsed.success) {
      throw new ApiError("Schema validation failed (degraded mode).", 503, json?.meta?.request_id, "SCHEMA_MISMATCH", true);
    }
    return parsed.data as T;
  };

  return doFetch();
}
