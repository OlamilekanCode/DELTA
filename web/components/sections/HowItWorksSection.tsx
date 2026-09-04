"use client";

import { motion, useReducedMotion } from "framer-motion";

const steps = [
  {
    n: "01",
    title: "Search a stock",
    body: "Enter any supported ticker — NVDA, TSLA, COIN, MSTR.",
    accent: "#6D4AFF",
    accentBg: "rgba(109,74,255,0.08)",
  },
  {
    n: "02",
    title: "Compare movement",
    body: "90-day Pearson correlation across aligned daily log returns.",
    accent: "#3D7BFF",
    accentBg: "rgba(61,123,255,0.08)",
  },
  {
    n: "03",
    title: "Explore the graph",
    body: "Node graph — score strength reflected in edge weight and distance.",
    accent: "#71F79F",
    accentBg: "rgba(113,247,159,0.08)",
  },
];

export default function HowItWorksSection() {
  const reduced = useReducedMotion();

  return (
    <section className="relative" aria-labelledby="how-heading">
      <div
        className="h-px w-full"
        style={{ background: "linear-gradient(90deg, transparent, rgba(109,74,255,0.35), rgba(61,123,255,0.25), transparent)" }}
        aria-hidden="true"
      />

      <div className="mx-auto max-w-7xl px-6 py-24 lg:px-8">
        {/* Header row */}
        <div className="mb-16 grid grid-cols-1 gap-6 lg:grid-cols-2 lg:gap-20">
          <motion.div
            initial={reduced ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <p className="mb-4 font-mono text-xs font-medium uppercase tracking-[0.25em] text-violet">
              How it works
            </p>
            <h2
              id="how-heading"
              className="font-heading font-bold leading-[0.95] text-text"
              style={{ fontSize: "clamp(2.4rem, 5vw, 4rem)" }}
            >
              Three steps.<br />
              <span
                style={{
                  background: "linear-gradient(135deg, #9B7BFF 0%, #6D4AFF 60%, #3D7BFF 100%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                Total clarity.
              </span>
            </h2>
          </motion.div>
          <motion.div
            className="flex items-end"
            initial={reduced ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.15 }}
          >
            <p className="max-w-sm font-mono text-sm leading-relaxed text-muted">
              DELTA runs historical analysis between any stock and the full crypto market.
              No wallet required. No sign-up. Just data.
            </p>
          </motion.div>
        </div>

        {/* Step strip */}
        <div className="grid grid-cols-1 overflow-hidden rounded-2xl border border-white/[0.09] sm:grid-cols-3">
          {steps.map((step, i) => (
            <motion.div
              key={step.n}
              className="group relative cursor-default border-b border-white/[0.09] p-8 transition-colors sm:border-b-0 sm:border-r last:border-0"
              style={{ background: "#080B12" }}
              initial={reduced ? false : { opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.1 + i * 0.1 }}
              whileHover={{ background: step.accentBg }}
            >
              {/* Number + dot */}
              <div className="mb-8 flex items-center justify-between">
                <span className="font-mono text-xs text-muted">{step.n}</span>
                <div
                  className="flex size-8 items-center justify-center rounded-full"
                  style={{
                    background: step.accentBg,
                    border: `1px solid ${step.accent}40`,
                  }}
                >
                  <div className="size-2 rounded-full" style={{ background: step.accent }} />
                </div>
              </div>

              <h3
                className="mb-3 font-heading text-2xl font-bold leading-tight text-text"
              >
                {step.title}
              </h3>
              <p className="font-mono text-sm leading-relaxed text-muted">{step.body}</p>

              {/* Hover accent underline */}
              <div
                className="absolute bottom-0 left-0 h-[2px] w-0 transition-all duration-500 group-hover:w-full"
                style={{ background: step.accent }}
                aria-hidden="true"
              />
            </motion.div>
          ))}
        </div>
      </div>

      <div
        className="h-px w-full"
        style={{ background: "linear-gradient(90deg, transparent, rgba(109,74,255,0.35), rgba(61,123,255,0.25), transparent)" }}
        aria-hidden="true"
      />
    </section>
  );
}
