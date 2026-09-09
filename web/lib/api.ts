import type {
  ApiAsset,
  ApiAssetHistoryOut,
  ApiAssetListOut,
  ApiExposuresResult,
  ApiGraphResult,
} from "@/lib/types";

const BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function apiFetch<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, opts);
  if (!res.ok) throw new Error(`API ${res.status}: ${url}`);
  return res.json() as Promise<T>;
}

// ── Assets ────────────────────────────────────────────────────────────────────

export function fetchAssets(type?: "crypto" | "stock"): Promise<ApiAssetListOut> {
  const url = type ? `/api/v1/assets?type=${type}` : "/api/v1/assets";
  return apiFetch<ApiAssetListOut>(url, { next: { revalidate: 300 } });
}

export function fetchAssetsSearch(q: string, type?: "crypto" | "stock"): Promise<ApiAssetListOut> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (type) params.set("type", type);
  return apiFetch<ApiAssetListOut>(`/api/v1/assets/search?${params}`, {
    next: { revalidate: 300 },
  });
}

export function fetchAsset(symbol: string): Promise<ApiAsset> {
  return apiFetch<ApiAsset>(`/api/v1/assets/${symbol}`, { next: { revalidate: 300 } });
}

export type ChartRange = "4H" | "1D" | "1W" | "1M" | "3M" | "1Y";

export function fetchAssetHistory(
  symbol: string,
  opts: { days?: number; range?: ChartRange } = {}
): Promise<ApiAssetHistoryOut> {
  const params = new URLSearchParams();
  if (opts.range) params.set("range", opts.range);
  else params.set("days", String(opts.days ?? 90));
  return apiFetch<ApiAssetHistoryOut>(`/api/v1/assets/${symbol}/history?${params}`, {
    next: { revalidate: 3600 },
  });
}

// ── Exposure Scores ───────────────────────────────────────────────────────────

export function fetchExposures(symbol: string): Promise<ApiExposuresResult> {
  return apiFetch<ApiExposuresResult>(`/api/v1/exposures/${symbol}`, {
    next: { revalidate: 3600 },
  });
}

// ── Graph ─────────────────────────────────────────────────────────────────────

export function fetchGraph(symbol: string, minScore = 0): Promise<ApiGraphResult> {
  return apiFetch<ApiGraphResult>(
    `/api/v1/graphs/${symbol}?min_score=${minScore}`,
    { next: { revalidate: 3600 } },
  );
}

// ── Correlation (backward compat) ─────────────────────────────────────────────

export async function fetchCorrelation(symbol: string, days = 90): Promise<unknown> {
  const res = await fetch(`${BASE}/api/v1/correlation/${symbol}?days=${days}`, {
    next: { revalidate: 3600 },
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
