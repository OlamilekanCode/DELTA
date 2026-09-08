"use client";

import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import type { ApiAssetHistoryOut } from "@/lib/types";
import AssetHistoryChartClient from "@/components/asset/AssetHistoryChartClient";
import ChartRangeSelector, { type ChartRange } from "@/components/charts/ChartRangeSelector";
import FreshnessLabel from "@/components/shared/FreshnessLabel";

const RANGE_LABELS: Record<ChartRange, string> = {
  "4H": "4-hour", "1D": "1-day", "1W": "1-week", "1M": "1-month", "3M": "3-month", "1Y": "1-year",
};

interface Props {
  symbol: string;
  color: string;
  initialHistory: ApiAssetHistoryOut;
}

async function fetchRangeHistory(symbol: string, range: ChartRange): Promise<ApiAssetHistoryOut> {
  const res = await fetch(`/api/assets/${symbol}/history?range=${range}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`history ${res.status}`);
  return res.json();
}

export default function AssetHistorySection({ symbol, color, initialHistory }: Props) {
  const [range, setRange] = useState<ChartRange>("3M");

  const { data: history = initialHistory, isFetching } = useQuery({
    queryKey: ["asset-history", symbol, range],
    queryFn: () => fetchRangeHistory(symbol, range),
    initialData: range === "3M" ? initialHistory : undefined,
    placeholderData: keepPreviousData,
  });

  const collectingData = history.collecting_data === true;

  return (
    <div className="overflow-hidden rounded-2xl border border-white/[0.09] bg-panel p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <ChartRangeSelector value={range} onChange={setRange} />
        <FreshnessLabel isDemo={history.is_demo ?? null} provider={history.provider} />
      </div>
      <div className="h-56 sm:h-72" aria-busy={isFetching}>
        {collectingData ? (
          <div className="flex h-full flex-col items-center justify-center gap-1 text-center">
            <p className="font-mono text-sm text-muted">
              Collecting {RANGE_LABELS[range]} intraday data…
            </p>
            <p className="font-mono text-xs text-muted/60">Check back after the next market session.</p>
          </div>
        ) : history.prices.length > 0 ? (
          <AssetHistoryChartClient prices={history.prices} color={color} />
        ) : (
          <div className="flex h-full items-center justify-center">
            <p className="font-mono text-sm text-muted">No price history available.</p>
          </div>
        )}
      </div>
    </div>
  );
}
