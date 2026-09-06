"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import type { ApiExposuresResult } from "@/lib/types";

const CATEGORY_COLORS: Record<string, { text: string; bg: string; border: string }> = {
  "Layer 1":     { text: "#F4C95D", bg: "rgba(244,201,93,0.08)",  border: "rgba(244,201,93,0.25)" },
  "Layer 2":     { text: "#3D7BFF", bg: "rgba(61,123,255,0.08)",  border: "rgba(61,123,255,0.25)" },
  "DeFi":        { text: "#9B7BFF", bg: "rgba(155,123,255,0.08)", border: "rgba(155,123,255,0.25)" },
  "Oracle/Data": { text: "#38BDF8", bg: "rgba(56,189,248,0.08)",  border: "rgba(56,189,248,0.25)" },
  "AI/Compute":  { text: "#71F79F", bg: "rgba(113,247,159,0.08)", border: "rgba(113,247,159,0.25)" },
  "Storage":     { text: "#FB923C", bg: "rgba(251,146,60,0.08)",  border: "rgba(251,146,60,0.25)" },
  "Memecoin":    { text: "#F472B6", bg: "rgba(244,114,182,0.08)", border: "rgba(244,114,182,0.25)" },
};
const DEFAULT = { text: "#9B7BFF", bg: "rgba(155,123,255,0.08)", border: "rgba(155,123,255,0.25)" };

function ScoreBar({ value, color }: { value: number; color: string }) {
  const reduced = useReducedMotion();
  return (
    <div className="h-1 w-full overflow-hidden rounded-full bg-panel2">
      <motion.div
        className="h-full rounded-full"
        style={{ background: color }}
        initial={{ width: 0 }}
        whileInView={{ width: `${value * 100}%` }}
        viewport={{ once: true }}
        transition={reduced ? { duration: 0 } : { duration: 0.8, ease: "easeOut" }}
      />
    </div>
  );
}

interface Props {
  exposures: ApiExposuresResult;
  stockSymbol: string;
}

export default function StockExposureList({ exposures, stockSymbol }: Props) {
  const reduced = useReducedMotion();

  if (exposures.scores.length === 0) {
    return (
      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <p className="font-mono text-sm text-muted">No Exposure Scores computed yet.</p>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-heading text-xl font-bold text-text">Crypto Exposure Scores</h2>
          <p className="mt-1 font-mono text-xs text-muted">
            90-day Pearson correlation · {exposures.scores[0]?.observations ?? "—"} aligned observations
          </p>
        </div>
        <Link
          href={`/graph/${stockSymbol}`}
          className="inline-flex items-center gap-1.5 rounded-lg border border-violet/30 bg-violet/10 px-4 py-2 font-mono text-xs text-violet-light transition-colors hover:border-violet/50 hover:bg-violet/20"
        >
          View exposure graph
          <svg className="size-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
          </svg>
        </Link>
      </div>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {exposures.scores.map((s, i) => {
          const c = CATEGORY_COLORS[s.category] ?? DEFAULT;
          return (
            <motion.div
              key={s.symbol}
              initial={reduced ? false : { opacity: 0, y: 8 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.35, delay: i * 0.04 }}
            >
              <Link
                href={`/asset/${s.symbol}`}
                className="block rounded-xl border border-white/[0.09] bg-panel p-4 transition-colors hover:border-violet/30 hover:bg-panel2"
              >
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold text-text">{s.symbol}</span>
                    <span
                      className="rounded-full px-1.5 py-0.5 font-mono text-[10px]"
                      style={{ color: c.text, background: c.bg, border: `1px solid ${c.border}` }}
                    >
                      {s.category}
                    </span>
                  </div>
                  <span className="font-mono text-sm font-bold" style={{ color: c.text }}>
                    {s.score.toFixed(2)}
                  </span>
                </div>
                <ScoreBar value={s.score} color={c.text} />
                <p className="mt-1.5 font-mono text-xs text-muted">{s.observations} observations</p>
              </Link>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
