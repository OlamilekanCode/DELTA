"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import type { ApiGraphResult } from "@/lib/types";

const Canvas = dynamic(() => import("./ExposureGraphCanvas"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center">
      <p className="font-mono text-sm text-muted">Loading graph…</p>
    </div>
  ),
});

type Interval = "historical" | "live";

async function fetchGraph(symbol: string, interval: Interval): Promise<ApiGraphResult> {
  const res = await fetch(`/api/graph/${symbol}?interval=${interval}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load ${interval} graph for ${symbol}: HTTP ${res.status}`);
  return res.json();
}

function IntervalToggle({ interval, onChange }: { interval: Interval; onChange: (i: Interval) => void }) {
  return (
    <div className="inline-flex rounded-lg border border-white/[0.09] bg-panel/90 p-0.5 backdrop-blur-sm">
      {(["historical", "live"] as const).map((opt) => (
        <button
          key={opt}
          onClick={() => onChange(opt)}
          className={`rounded-md px-2.5 py-1 font-mono text-[11px] uppercase tracking-wide transition-colors ${
            interval === opt ? "bg-violet/20 text-violet-light" : "text-muted hover:text-text"
          }`}
        >
          {opt === "historical" ? "Historical" : "Live"}
        </button>
      ))}
    </div>
  );
}

export default function ExposureGraphCanvasClient({
  graphData: initialGraphData,
}: {
  graphData: ApiGraphResult | null;
}) {
  const [interval, setInterval] = useState<Interval>("historical");
  const symbol = initialGraphData?.stock.symbol ?? null;

  const { data, isLoading } = useQuery({
    queryKey: ["graph", symbol, interval],
    queryFn: () => fetchGraph(symbol as string, interval),
    enabled: symbol != null,
    initialData: interval === "historical" && initialGraphData ? initialGraphData : undefined,
    refetchInterval: interval === "live" ? 60_000 : false,
    refetchIntervalInBackground: false,
  });

  const graphData = data ?? null;

  return (
    <div className="relative h-full w-full">
      <div className="absolute right-4 top-4 z-10">
        <IntervalToggle interval={interval} onChange={setInterval} />
      </div>

      {isLoading ? (
        <div className="flex h-full items-center justify-center">
          <p className="font-mono text-sm text-muted">Loading graph…</p>
        </div>
      ) : graphData && graphData.status === "collecting_data" ? (
        <div className="flex h-full items-center justify-center">
          <div className="text-center">
            <p className="font-mono text-sm text-muted">
              Collecting live data — {graphData.current_count ?? 0}/{graphData.required_count ?? "—"} completed
              30-minute intervals.
            </p>
            {graphData.estimated_ready && (
              <p className="mt-2 font-mono text-xs text-muted/60">Estimated ready {graphData.estimated_ready}</p>
            )}
            {graphData.market_is_open === false && (
              <p className="mt-2 font-mono text-xs text-blue">US market closed</p>
            )}
          </div>
        </div>
      ) : (
        <Canvas graphData={graphData} />
      )}
    </div>
  );
}
