import type {
  ApiAsset,
  ApiAssetHistoryOut,
  ApiAssetListOut,
  ApiExposuresResult,
  ApiGraphResult,
} from "@/lib/types";
import { backendUrl, getSessionToken, isBackendConfigured } from "@/lib/bff";
import type { ChartRange } from "@/lib/api";

const PUBLIC_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiRequestError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/**
 * Server Component data fetcher that forwards the caller's session (if any)
 * as a Bearer header to the backend — this is what lets an authenticated
 * holder's server-rendered page actually see holder-only data, instead of
 * always hitting the backend as an anonymous guest.
 *
 * With a session present: always goes through BACKEND_API_URL (server-only)
 * with `cache: "no-store"` — authenticated/entitlement-specific responses
 * must never be cached or shared between users.
 * Without a session: falls back to the public API origin with normal ISR
 * revalidation, identical to the pre-existing guest behavior.
 */
async function serverFetch<T>(path: string, opts: { revalidate?: number } = {}): Promise<T> {
  const token = await getSessionToken();

  if (token) {
    if (!isBackendConfigured()) {
      throw new ApiRequestError(503, "backend_not_configured");
    }
    const res = await fetch(backendUrl(path), {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!res.ok) throw new ApiRequestError(res.status, `API ${res.status}: ${path}`);
    return res.json() as Promise<T>;
  }

  const res = await fetch(`${PUBLIC_BASE}${path}`, {
    next: { revalidate: opts.revalidate ?? 300 },
  });
  if (!res.ok) throw new ApiRequestError(res.status, `API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

export function fetchAssetsAuthed(type?: "crypto" | "stock"): Promise<ApiAssetListOut> {
  const url = type ? `/api/v1/assets?type=${type}` : "/api/v1/assets";
  return serverFetch<ApiAssetListOut>(url, { revalidate: 300 });
}

export function fetchAssetAuthed(symbol: string): Promise<ApiAsset> {
  return serverFetch<ApiAsset>(`/api/v1/assets/${symbol}`, { revalidate: 300 });
}

export function fetchAssetHistoryAuthed(
  symbol: string,
  opts: { days?: number; range?: ChartRange } = {}
): Promise<ApiAssetHistoryOut> {
  const params = new URLSearchParams();
  if (opts.range) params.set("range", opts.range);
  else params.set("days", String(opts.days ?? 90));
  return serverFetch<ApiAssetHistoryOut>(`/api/v1/assets/${symbol}/history?${params}`, { revalidate: 3600 });
}

export function fetchExposuresAuthed(symbol: string): Promise<ApiExposuresResult> {
  return serverFetch<ApiExposuresResult>(`/api/v1/exposures/${symbol}`, { revalidate: 3600 });
}

export function fetchGraphAuthed(symbol: string, minScore = 0): Promise<ApiGraphResult> {
  return serverFetch<ApiGraphResult>(`/api/v1/graphs/${symbol}?min_score=${minScore}`, { revalidate: 3600 });
}
