"use client";

import dynamic from "next/dynamic";
import { motion, useReducedMotion } from "framer-motion";
import DemoDataBadge from "@/components/shared/DemoDataBadge";
import { topExposureScores } from "@/lib/fixtures/exposure-scores";

const NVDAChart = dynamic(() => import("./NVDAChart"), {
  ssr: false,
  loading: () => (
    <div className="h-64 w-full animate-pulse rounded-xl bg-panel2" aria-label="Loading chart" />
  ),
});

const CATEGORY_COLORS: Record<string, { text: string; bg: string; border: string }> = {
  "BTC Ecosystem": { text: "#F4C95D", bg: "rgba(244,201,93,0.08)", border: "rgba(244,201,93,0.25)" },
  "DeFi":          { text: "#3D7BFF", bg: "rgba(61,123,255,0.08)", border: "rgba(61,123,255,0.25)" },
  "AI":            { text: "#71F79F", bg: "rgba(113,247,159,0.08)", border: "rgba(113,247,159,0.25)" },
};

function ScoreBar({ value, color }: { value: number; color: string }) {
  const reduced = useReducedMotion();
  return (
    <div className="h-1 w-full overflow-hidden rounded-full bg-panel2" role="presentation">
      <motion.div
        className="h-full rounded-full"
        style={{ background: color }}
        initial={{ width: 0 }}
        whileInView={{ width: `${value * 100}%` }}
        viewport={{ once: true }}
        transition={reduced ? { duration: 0 } : { duration: 1, delay: 0.3, ease: "easeOut" }}
      />
    </div>
  );
}

export default function NVDAExampleSection() {
  const reduced = useReducedMotion();

  return (
    <section
      className="relative overflow-hidden"
      aria-labelledby="nvda-heading"
      style={{ background: "linear-gradient(180deg, #030508 0%, #060414 50%, #030508 100%)" }}
    >
      {/* Subtle violet section tint */}
      <div
        className="pointer-events-none absolute inset-0"
        aria-hidden="true"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 50% 50%, rgba(109,74,255,0.06) 0%, transparent 70%)",
        }}
      />

      <div className="relative mx-auto max-w-7xl px-6 py-24 lg:px-8">
        {/* Eyebrow */}
        <motion.div
          className="mb-3 flex items-center gap-3"
          initial={reduced ? false : { opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <p className="font-mono text-xs font-medium uppercase tracking-[0.25em] text-violet">
            Live example
          </p>
          <DemoDataBadge />
        </motion.div>

        {/* Heading */}
        <motion.div
          initial={reduced ? false : { opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.05 }}
        >
          <h2
            id="nvda-heading"
            className="font-heading font-bold leading-[0.92] text-text"
            style={{ fontSize: "clamp(2.6rem, 6vw, 5rem)" }}
          >
            NVDA
            <span className="mx-4 font-mono text-muted" style={{ fontSize: "40%" }}>↔</span>
            <span
              style={{
                background: "linear-gradient(135deg, #9B7BFF 0%, #6D4AFF 60%, #3D7BFF 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              Crypto.
            </span>
          </h2>
          <p className="mt-4 font-mono text-sm text-muted">
            90-day historical relationship · 63 aligned observations
          </p>
        </motion.div>

        {/* Big score display row */}
        <motion.div
          className="my-12 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-white/[0.09] sm:grid-cols-4"
          style={{ background: "rgba(255,255,255,0.05)" }}
          initial={reduced ? false : { opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          {topExposureScores.map((s, i) => {
            const cat = CATEGORY_COLORS[s.category] ?? { text: "#9B7BFF", bg: "rgba(155,123,255,0.08)", border: "rgba(155,123,255,0.25)" };
            return (
              <motion.div
                key={s.symbol}
                className="group relative flex flex-col items-center justify-center gap-2 bg-panel px-4 py-8 text-center transition-colors hover:bg-panel2"
                initial={reduced ? false : { opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: 0.15 + i * 0.08 }}
              >
                <motion.span
                  className="font-heading font-bold leading-none"
                  style={{ fontSize: "clamp(2rem, 4vw, 3.5rem)", color: cat.text }}
                  initial={reduced ? false : { scale: 0.7, opacity: 0 }}
                  whileInView={{ scale: 1, opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: 0.2 + i * 0.08, ease: "backOut" }}
                >
                  {s.score.toFixed(2)}
                </motion.span>
                <span className="font-mono text-base font-medium text-text">{s.symbol}</span>
                <span
                  className="rounded-full px-2 py-0.5 font-mono text-[10px] font-medium"
                  style={{ color: cat.text, background: cat.bg, border: `1px solid ${cat.border}` }}
                >
                  {s.category}
                </span>
                {/* Hover underline */}
                <div
                  className="absolute bottom-0 left-0 h-[2px] w-0 transition-all duration-500 group-hover:w-full"
                  style={{ background: cat.text }}
                  aria-hidden="true"
                />
              </motion.div>
            );
          })}
        </motion.div>

        {/* Chart + score bars */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
          {/* Chart — 3/5 */}
          <motion.div
            className="lg:col-span-3"
            initial={reduced ? false : { opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <div className="overflow-hidden rounded-2xl border border-white/[0.09] bg-panel p-5">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <p className="font-mono text-xs text-muted">Normalized performance (base = 100)</p>
                <div className="flex items-center gap-4 font-mono text-xs">
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block size-2 rounded-full bg-violet" />NVDA
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block size-2 rounded-full bg-amber" />BTC
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block size-2 rounded-full bg-blue" />ETH
                  </span>
                </div>
              </div>
              <div className="h-64 w-full">
                <NVDAChart />
              </div>
            </div>
          </motion.div>

          {/* Score bars — 2/5 */}
          <motion.div
            className="flex flex-col gap-3 lg:col-span-2"
            initial={reduced ? false : { opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.25 }}
          >
            <p className="font-mono text-xs font-medium uppercase tracking-widest text-muted">
              Top Exposure Scores
            </p>
            {topExposureScores.map((s, i) => {
              const cat = CATEGORY_COLORS[s.category] ?? { text: "#9B7BFF", bg: "rgba(155,123,255,0.08)", border: "rgba(155,123,255,0.25)" };
              return (
                <motion.article
                  key={s.symbol}
                  className="rounded-xl border border-white/[0.09] bg-panel p-4 transition-colors hover:border-violet/30 hover:bg-panel2"
                  initial={reduced ? false : { opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: 0.3 + i * 0.06 }}
                >
                  <div className="mb-2 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-medium text-text">{s.symbol}</span>
                      <span
                        className="rounded-full px-1.5 py-0.5 font-mono text-[10px]"
                        style={{ color: cat.text, background: cat.bg }}
                      >
                        {s.category}
                      </span>
                    </div>
                    <span
                      className="font-mono text-sm font-bold"
                      style={{ color: cat.text }}
                    >
                      {s.score.toFixed(2)}
                    </span>
                  </div>
                  <ScoreBar value={s.score} color={cat.text} />
                  <p className="mt-1.5 font-mono text-[10px] text-muted">
                    {s.observations} observations
                  </p>
                </motion.article>
              );
            })}
          </motion.div>
        </div>
      </div>
    </section>
  );
}
