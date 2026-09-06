"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import DemoDataBadge from "@/components/shared/DemoDataBadge";

const categories = [
  { label: "AI / Technology",  pct: 37, color: "#71F79F", bg: "rgba(113,247,159,0.12)" },
  { label: "DeFi",             pct: 24, color: "#3D7BFF", bg: "rgba(61,123,255,0.12)" },
  { label: "BTC Ecosystem",    pct: 22, color: "#F4C95D", bg: "rgba(244,201,93,0.12)" },
  { label: "Other",            pct: 17, color: "#6B7280", bg: "rgba(107,114,128,0.12)" },
];

export default function PortfolioPreview() {
  const reduced = useReducedMotion();

  return (
    <section
      className="relative overflow-hidden"
      aria-labelledby="portfolio-heading"
      style={{
        background: "linear-gradient(180deg, #030508 0%, #0A0520 50%, #030508 100%)",
      }}
    >
      {/* Ambient violet glow */}
      <div
        className="pointer-events-none absolute inset-0"
        aria-hidden="true"
        style={{
          background:
            "radial-gradient(ellipse 70% 50% at 30% 50%, rgba(109,74,255,0.1) 0%, transparent 65%)",
        }}
      />

      <div className="relative mx-auto max-w-7xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8 lg:py-24">
        <div className="grid grid-cols-1 gap-8 sm:gap-10 lg:grid-cols-2 lg:gap-16 lg:items-center">

          {/* Left — copy */}
          <motion.div
            initial={reduced ? false : { opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7 }}
          >
            <p className="mb-4 font-mono text-xs font-medium uppercase tracking-[0.25em] text-violet">
              Portfolio Exposure
            </p>
            <h2
              id="portfolio-heading"
              className="font-heading font-bold leading-[0.92] text-text"
              style={{ fontSize: "clamp(2.4rem, 5vw, 4.2rem)" }}
            >
              Know what your<br />
              <span
                style={{
                  background: "linear-gradient(135deg, #9B7BFF 0%, #6D4AFF 60%, #3D7BFF 100%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                crypto holds.
              </span>
            </h2>
            <p className="mt-6 max-w-sm font-mono text-sm leading-relaxed text-muted">
              Connect a wallet and Synthetic Exposure reads your public on-chain holdings — read-only, no transaction required. See your category exposure and weighted stock correlation score.
            </p>

            {/* Weighted score callout */}
            <div
              className="mt-8 inline-flex items-center gap-4 rounded-2xl border px-6 py-4"
              style={{
                background: "rgba(109,74,255,0.08)",
                borderColor: "rgba(109,74,255,0.25)",
              }}
            >
              <div>
                <p className="font-mono text-xs uppercase tracking-widest text-muted">Weighted NVDA Score</p>
                <p
                  className="font-heading text-3xl font-bold sm:text-4xl"
                  style={{ color: "#9B7BFF" }}
                >
                  0.42
                </p>
              </div>
              <div className="h-10 w-px bg-white/10" />
              <DemoDataBadge />
            </div>

            <div className="mt-8">
              <Link
                href="/portfolio"
                className="inline-flex items-center gap-2 rounded-lg px-6 py-3 text-sm font-semibold text-white transition-all active:scale-95"
                style={{
                  background: "linear-gradient(135deg, #6D4AFF 0%, #4F35CC 100%)",
                  boxShadow: "0 0 24px rgba(109,74,255,0.35)",
                }}
              >
                Connect wallet to analyze
                <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              </Link>
            </div>
          </motion.div>

          {/* Right — big category bars */}
          <motion.div
            initial={reduced ? false : { opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, delay: 0.1 }}
          >
            <p className="mb-6 font-mono text-xs font-medium uppercase tracking-widest text-muted">
              Portfolio breakdown
            </p>
            <div className="space-y-5">
              {categories.map((cat, i) => (
                <motion.div
                  key={cat.label}
                  initial={reduced ? false : { opacity: 0, x: 20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: 0.2 + i * 0.08 }}
                >
                  <div className="mb-2 flex items-end justify-between">
                    <span className="font-mono text-xs text-muted">{cat.label}</span>
                    <motion.span
                      className="font-heading text-xl font-bold sm:text-2xl"
                      style={{ color: cat.color }}
                      initial={reduced ? false : { opacity: 0 }}
                      whileInView={{ opacity: 1 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.6, delay: 0.3 + i * 0.08 }}
                    >
                      {cat.pct}%
                    </motion.span>
                  </div>
                  <div
                    className="h-2.5 w-full overflow-hidden rounded-full sm:h-3"
                    style={{ background: "rgba(255,255,255,0.05)" }}
                    role="presentation"
                  >
                    <motion.div
                      className="h-full rounded-full"
                      style={{ background: cat.color }}
                      initial={{ width: 0 }}
                      whileInView={{ width: `${cat.pct}%` }}
                      viewport={{ once: true }}
                      transition={reduced ? { duration: 0 } : { duration: 1, delay: 0.35 + i * 0.08, ease: "easeOut" }}
                    />
                  </div>
                </motion.div>
              ))}
            </div>

            <p className="mt-6 font-mono text-xs text-muted/50">
              Demo data · read-only wallet connection · not financial advice
            </p>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
