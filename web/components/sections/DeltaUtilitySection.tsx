"use client";

import { motion, useReducedMotion } from "framer-motion";

type FeatureStatus = "available" | "soon" | "future";

const features: { label: string; status: FeatureStatus; note: string; desc: string }[] = [
  { label: "Exposure Scores",           status: "available", note: "Live now",              desc: "0–1 Pearson correlation score across 8 stocks × 30 crypto" },
  { label: "Exposure Graph",            status: "available", note: "Live now",              desc: "Interactive graph of stock ↔ crypto relationships" },
  { label: "Price History",             status: "available", note: "Live now",              desc: "90-day daily OHLCV for all assets in the universe" },
  { label: "Portfolio Exposure",        status: "soon",      note: "Coming soon",           desc: "Wallet-level exposure breakdown and weighted score" },
  { label: "Advanced Exposure Scores",  status: "soon",      note: "Coming soon",           desc: "Extended universe, finer precision, longer lookback windows" },
  { label: "Deeper Graph Levels",       status: "soon",      note: "Coming soon",           desc: "Expand beyond top-12 connections per stock" },
  { label: "Real-Time Alerts",          status: "soon",      note: "Coming soon",           desc: "Score change notifications" },
  { label: "Automated Baskets",         status: "future",    note: "Future",                desc: "Thematic index baskets by exposure cluster" },
  { label: "Developer API",             status: "future",    note: "Future",                desc: "REST API for programmatic access" },
];

const statusConfig = {
  available: { color: "#71F79F", bg: "rgba(113,247,159,0.08)", border: "rgba(113,247,159,0.25)", dot: "#71F79F" },
  soon:      { color: "#F4C95D", bg: "rgba(244,201,93,0.08)",  border: "rgba(244,201,93,0.25)",  dot: "#F4C95D" },
  future:    { color: "#6B7280", bg: "rgba(107,114,128,0.08)", border: "rgba(107,114,128,0.2)",  dot: "#6B7280" },
} as const;

export default function DeltaUtilitySection() {
  const reduced = useReducedMotion();

  return (
    <section className="relative overflow-hidden" aria-labelledby="delta-utility-heading">
      <div
        className="h-px w-full"
        style={{ background: "linear-gradient(90deg, transparent, rgba(109,74,255,0.35), rgba(61,123,255,0.25), transparent)" }}
        aria-hidden="true"
      />

      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8 lg:py-24">
        {/* Header */}
        <div className="mb-12 grid grid-cols-1 gap-8 lg:grid-cols-2 lg:gap-16">
          <motion.div
            initial={reduced ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <p className="mb-4 font-mono text-xs font-medium uppercase tracking-[0.25em] text-violet">
              $DELTA utility token
            </p>
            <h2
              id="delta-utility-heading"
              className="font-heading font-bold leading-[0.92] text-text"
              style={{ fontSize: "clamp(2.4rem, 5vw, 4rem)" }}
            >
              Unlock deeper<br />
              <span
                style={{
                  background: "linear-gradient(135deg, #9B7BFF 0%, #6D4AFF 60%, #3D7BFF 100%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                market insight.
              </span>
            </h2>
          </motion.div>
          <motion.div
            className="flex items-end"
            initial={reduced ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <p className="max-w-sm font-mono text-sm leading-relaxed text-muted">
              Hold $DELTA to unlock advanced analytics when they launch. Free users can explore the public Exposure Scores and Graph today.
            </p>
          </motion.div>
        </div>

        {/* Feature table */}
        <motion.div
          className="overflow-hidden rounded-2xl border border-white/[0.09]"
          initial={reduced ? false : { opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.15 }}
        >
          {/* Table header */}
          <div className="grid grid-cols-[1fr_auto] border-b border-white/[0.09] bg-panel2 px-4 py-3 sm:grid-cols-[auto_1fr_auto] sm:px-6">
            <span className="hidden font-mono text-xs uppercase tracking-widest text-muted sm:block">Feature</span>
            <span className="font-mono text-xs uppercase tracking-widest text-muted sm:text-center">Description</span>
            <span className="font-mono text-xs uppercase tracking-widest text-muted text-right">Status</span>
          </div>

          {/* Rows */}
          {features.map((f, i) => {
            const s = statusConfig[f.status];
            return (
              <motion.div
                key={f.label}
                className="group grid grid-cols-[1fr_auto] items-center gap-3 border-b border-white/[0.06] bg-panel px-4 py-4 transition-colors hover:bg-panel2 last:border-0 sm:grid-cols-[180px_1fr_auto] sm:gap-4 sm:px-6 lg:grid-cols-[220px_1fr_auto]"
                initial={reduced ? false : { opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.35, delay: 0.02 * i }}
              >
                {/* Label */}
                <div className="flex items-center gap-3">
                  <div className="size-1.5 shrink-0 rounded-full" style={{ background: s.dot }} aria-hidden="true" />
                  <span className="font-mono text-sm font-medium text-text">{f.label}</span>
                </div>

                {/* Description */}
                <span className="hidden font-mono text-xs text-muted sm:block">{f.desc}</span>

                {/* Badge */}
                <span
                  className="shrink-0 rounded-full border px-2.5 py-1 font-mono text-[10px] font-medium"
                  style={{ color: s.color, background: s.bg, borderColor: s.border }}
                >
                  {f.note}
                </span>
              </motion.div>
            );
          })}
        </motion.div>
      </div>

      <div
        className="h-px w-full"
        style={{ background: "linear-gradient(90deg, transparent, rgba(109,74,255,0.35), rgba(61,123,255,0.25), transparent)" }}
        aria-hidden="true"
      />
    </section>
  );
}
