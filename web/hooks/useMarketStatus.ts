"use client";

import { useQuery } from "@tanstack/react-query";

export interface MarketStatus {
  is_open: boolean;
  timezone: string;
  last_close: string;
  next_open: string;
  current_bucket: string | null;
  status_reason: string;
}

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
const POLL_INTERVAL_MS = 60_000;

async function fetchMarketStatus(): Promise<MarketStatus> {
  const res = await fetch(`${API_BASE}/api/v1/market-status`, { cache: "no-store" });
  if (!res.ok) throw new Error(`market-status ${res.status}`);
  return res.json();
}

export function useMarketStatus(): MarketStatus | null {
  const { data } = useQuery({
    queryKey: ["market-status"],
    queryFn: fetchMarketStatus,
    refetchInterval: POLL_INTERVAL_MS,
    refetchIntervalInBackground: false,
  });
  return data ?? null;
}
