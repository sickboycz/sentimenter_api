import { ApiEnvelope, ApiListEnvelope } from "./schemas";

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

/** Validate API envelope with Zod (v1.2). Logs warning on failure, returns raw if invalid. */
function validateResponse<T>(raw: unknown, hasPagination = false): T {
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

export async function apiGet<T>(path: string, apiKey?: string, validate = true): Promise<T> {
  const url = new URL(path, API_BASE);
  const headers: HeadersInit = {};
  if (apiKey) {
    url.searchParams.set("api_key", apiKey);
    headers["X-API-Key"] = apiKey;
  }

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: Object.keys(headers).length ? headers : undefined,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  const raw = (await res.json()) as T;
  if (validate) {
    return validateResponse<T>(raw, path.includes("/topics/index") || path.includes("/news/clusters"));
  }
  return raw;
}
