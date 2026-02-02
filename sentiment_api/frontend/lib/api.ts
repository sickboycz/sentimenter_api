import { ApiEnvelope, ApiListEnvelope } from "./schemas";

/** Thrown on 503; UI should show graceful degraded message. */
export class ApiDegradedError extends Error {
  constructor(message = "Service temporarily unavailable") {
    super(message);
    this.name = "ApiDegradedError";
  }
}

/** sentiment_api base URL (default port 8080). In browser, when unset, use same host as page to avoid Private Network Access block (e.g. page at http://SERVER:3000 → API at http://SERVER:8080). */
export const API_BASE =
  (typeof window !== "undefined" && !process.env.NEXT_PUBLIC_API_BASE_URL)
    ? `${window.location.protocol}//${window.location.hostname}:8080`
    : (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080");

/** API key (set via NEXT_PUBLIC_API_KEY or pass to apiGet) */
export const getDefaultApiKey = () =>
  (typeof window !== "undefined" ? localStorage.getItem("sentiment_api_key") : null) ??
  process.env.NEXT_PUBLIC_API_KEY ??
  "";

/** Paths that return non-envelope format (plain object, no meta/errors). Skip validation. */
const NON_ENVELOPE_PATHS = ["/v1/health", "/v1/status"];

/** Validate API envelope with Zod (v1.2). Logs warning on failure, returns raw if invalid. */
function validateResponse<T>(raw: unknown, path: string, hasPagination = false): T {
  if (NON_ENVELOPE_PATHS.some((p) => path.startsWith(p))) return raw as T;
  try {
    if (hasPagination) {
      ApiListEnvelope.parse(raw);
    } else {
      ApiEnvelope.parse(raw);
    }
  } catch (e) {
    if (typeof console !== "undefined" && console.warn) {
      console.warn("[api] Response validation warning:", e);
    }
  }
  return raw as T;
}

const MAX_429_RETRIES = 2;

function parseRetryAfter(header: string | null): number {
  if (!header) return 1000;
  const s = header.trim();
  const n = parseInt(s, 10);
  if (!Number.isNaN(n)) return n <= 60 ? n * 1000 : 60000; // seconds; cap at 60s
  return 1000; // fallback
}

async function doFetch<T>(
  url: string,
  headers: HeadersInit | undefined,
  path: string,
  validate: boolean,
  attempt: number
): Promise<T> {
  const res = await fetch(url, { cache: "no-store", headers });
  if (res.status === 429 && attempt < MAX_429_RETRIES) {
    const delay = parseRetryAfter(res.headers.get("Retry-After"));
    await new Promise((r) => setTimeout(r, delay));
    return doFetch<T>(url, headers, path, validate, attempt + 1);
  }
  if (res.status === 503) {
    throw new ApiDegradedError("Service temporarily unavailable (503)");
  }
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  const raw = (await res.json()) as T;
  if (validate) {
    const hasPagination = path.includes("/topics/index") || path.includes("/news/clusters");
    return validateResponse<T>(raw, path, hasPagination);
  }
  return raw;
}

export async function apiGet<T>(path: string, apiKey?: string, validate = true): Promise<T> {
  const url = new URL(path, API_BASE);
  const headers: HeadersInit = {};
  if (apiKey) {
    url.searchParams.set("api_key", apiKey);
    headers["X-API-Key"] = apiKey;
  }
  return doFetch<T>(
    url.toString(),
    Object.keys(headers).length ? headers : undefined,
    path,
    validate,
    0
  );
}
