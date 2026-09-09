"use client";

import { useQuery } from "@tanstack/react-query";
import { motion, useReducedMotion } from "framer-motion";
import type { ApiIntradayResult } from "@/lib/types";
import { formatScore } from "@/lib/format";

const POLL_INTERVAL_MS = 60_000;
const SCORE_POS_COLOR = "#9B7BFF";
const SCORE_INV_COLOR = "#FB923C";

interface Props {
  symbol: string;
}

async function fetchIntraday(symbol: string): Promise<ApiIntradayResult> {
  const res = await fetch(`/api/intraday/${symbol}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to load live exposure for ${symbol}: HTTP ${res.status}`);
  }
  return res.json();
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function FreshnessPill({ result }: { result: ApiIntradayResult }) {
  if (result.freshness === "market_closed") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-blue/40 bg-blue/10 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-widest text-blue">
        <span className="size-1.5 rounded-full bg-blue" aria-hidden="true" />
        US market closed
      </span>
    );
  }
  if (result.freshness === "stale") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-amber/40 bg-amber/10 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-widest text-amber">
        Stale
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-green/40 bg-green/10 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-widest text-green">
      <span className="size-1.5 rounded-full bg-green animate-pulse" aria-hidden="true" />
      Live
    </span>
  );
}

export default function LiveExposureSection({ symbol }: Props) {
  const reduced = useReducedMotion();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["intraday", symbol],
    queryFn: () => fetchIntraday(symbol),
    refetchInterval: POLL_INTERVAL_MS,
    refetchIntervalInBackground: false,
  });

  if (isError) {
    return (
      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <p className="font-mono text-sm text-muted">Live Exposure is temporarily unavailable.</p>
      </section>
    );
  }

  if (isLoading || !data) {
    return (
      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="h-24 animate-pulse rounded-2xl border border-white/[0.09] bg-panel" />
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-heading text-xl font-bold text-text">Live Exposure</h2>
            <FreshnessPill result={data} />
          </div>
          <p className="mt-1 max-w-2xl font-mono text-xs text-muted">
            A rolling 30-minute-candle Pearson correlation calculated from recent completed market intervals —
            not a tick-by-tick prediction.
          </p>
        </div>
        <div className="text-right font-mono text-xs text-muted">
          {data.data_ts && <p>Score as of {formatTime(data.data_ts)}</p>}
          {!data.market_is_open && data.next_market_open && (
            <p className="mt-0.5">Next open {formatTime(data.next_market_open)}</p>
          )}
        </div>
      </div>

      {data.status === "collecting_data" ? (
        <div className="rounded-2xl border border-white/[0.09] bg-panel p-5">
          <p className="font-mono text-sm text-muted">
            Collecting data — {data.current_count ?? 0}/{data.required_count ?? "—"} completed 30-minute intervals.
          </p>
          {data.estimated_ready && (
            <p className="mt-1 font-mono text-xs text-muted/60">Estimated ready {data.estimated_ready}</p>
          )}
        </div>
      ) : data.scores.length === 0 ? (
        <div className="rounded-2xl border border-white/[0.09] bg-panel p-5">
          <p className="font-mono text-sm text-muted">No live Exposure Scores available yet.</p>
        </div>
      ) : (
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {data.scores.map((s, i) => (
            <motion.div
              key={s.symbol}
              initial={reduced ? false : { opacity: 0, y: 8 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.3, delay: i * 0.03 }}
              className="rounded-xl border border-white/[0.09] bg-panel p-4"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-sm font-bold text-text">{s.symbol}</span>
                <span
                  className="font-mono text-sm font-bold"
                  style={{ color: s.score >= 0 ? SCORE_POS_COLOR : SCORE_INV_COLOR }}
                >
                  {formatScore(s.score)}
                </span>
              </div>
              <p className="mt-1.5 font-mono text-xs text-muted">{s.observations} intervals</p>
            </motion.div>
          ))}
        </div>
      )}
    </section>
  );
}
