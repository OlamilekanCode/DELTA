"use client";

import Link from "next/link";
import dynamic from "next/dynamic";

const HeroGraph = dynamic(() => import("./HeroGraph"), {
  ssr: false,
  loading: () => (
    <div
      className="w-full"
      style={{ aspectRatio: "1 / 1", maxWidth: 520 }}
      aria-label="Loading Exposure Graph"
    />
  ),
});

const bullets = [
  {
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="size-4" aria-hidden="true">
        <path d="M10 2a8 8 0 100 16A8 8 0 0010 2zm0 1.5a6.5 6.5 0 110 13 6.5 6.5 0 010-13zM10 6a1 1 0 00-1 1v3H6a1 1 0 100 2h4a1 1 0 001-1V7a1 1 0 00-1-1z" />
      </svg>
    ),
    title: "Cross-Market Exposure",
    body: "Connect TradFi and crypto",
  },
  {
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="size-4" aria-hidden="true">
        <path fillRule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 0l-2 2a1 1 0 101.414 1.414L8 10.414l1.293 1.293a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
      </svg>
    ),
    title: "Real Correlation",
    body: "90-day aligned observations",
  },
  {
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="size-4" aria-hidden="true">
        <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
      </svg>
    ),
    title: "Portfolio Insights",
    body: "Wallet-level exposure analysis",
  },
];

export default function HeroSection() {
  return (
    <section
      className="relative overflow-hidden"
      style={{ minHeight: "100svh" }}
      aria-labelledby="hero-heading"
    >
      {/* Background layers */}
      <div className="pointer-events-none absolute inset-0 dot-grid opacity-50" aria-hidden="true" />
      <div
        className="pointer-events-none absolute right-0 top-0 h-full w-1/2"
        aria-hidden="true"
        style={{
          background:
            "radial-gradient(ellipse 70% 80% at 70% 40%, rgba(109,74,255,0.13) 0%, rgba(61,123,255,0.06) 40%, transparent 70%)",
        }}
      />
      {/* Bottom fade */}
      <div
        className="pointer-events-none absolute bottom-0 inset-x-0 h-32"
        aria-hidden="true"
        style={{ background: "linear-gradient(to bottom, transparent, #05060A)" }}
      />

      <div className="relative mx-auto flex min-h-screen max-w-7xl flex-col items-center px-6 pt-28 pb-12 lg:flex-row lg:items-center lg:gap-0 lg:px-8">
        {/* ── Left: Copy ── */}
        <div className="flex flex-col items-start lg:w-[46%] lg:pr-8">
          {/* Eyebrow */}
          <div className="mb-6 flex items-center gap-2">
            <span className="inline-block size-1.5 rounded-full bg-green" aria-hidden="true" />
            <p className="font-mono text-[10px] font-medium uppercase tracking-[0.25em] text-muted">
              The Synthetic Exposure Layer
            </p>
          </div>

          {/* Heading */}
          <h1 id="hero-heading" className="font-heading font-bold leading-[1.0] text-text"
            style={{ fontSize: "clamp(2.8rem, 7vw, 5.5rem)" }}>
            <span
              style={{
                background: "linear-gradient(135deg, #9B7BFF 0%, #6D4AFF 50%, #3D7BFF 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              Map
            </span>{" "}
            the Market.
          </h1>

          {/* Body */}
          <p className="mt-5 max-w-sm text-[1.05rem] leading-relaxed text-muted">
            DELTA maps how stocks and crypto move together using historical market data.
          </p>

          {/* Bullets */}
          <ul className="mt-8 space-y-3" role="list">
            {bullets.map((b) => (
              <li key={b.title} className="flex items-center gap-3">
                <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-violet/15 text-violet-light">
                  {b.icon}
                </span>
                <div>
                  <span className="text-sm font-medium text-text">{b.title}</span>
                  <span className="ml-2 font-mono text-xs text-muted">{b.body}</span>
                </div>
              </li>
            ))}
          </ul>

          {/* CTAs */}
          <div className="mt-10 flex flex-wrap items-center gap-3">
            <Link
              href="/asset/NVDA"
              className="inline-flex items-center gap-2 rounded-lg px-6 py-3 text-sm font-semibold text-white transition-all active:scale-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet"
              style={{
                background: "linear-gradient(135deg, #6D4AFF 0%, #4F35CC 100%)",
                boxShadow: "0 0 24px rgba(109,74,255,0.35), inset 0 1px 0 rgba(255,255,255,0.1)",
              }}
            >
              Explore NVDA
              <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
            </Link>

            <Link
              href="/portfolio"
              className="inline-flex items-center gap-2 rounded-lg border border-white/[0.12] bg-white/[0.03] px-6 py-3 text-sm font-semibold text-text backdrop-blur-sm transition-all hover:border-violet/40 hover:bg-white/[0.06] active:scale-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet"
            >
              Connect wallet
            </Link>
          </div>

          {/* Disclaimer */}
          <p className="mt-6 font-mono text-[10px] uppercase tracking-widest text-muted/50">
            Analytical tool · Not financial advice
          </p>
        </div>

        {/* ── Right: Graph ── */}
        <div className="flex w-full items-center justify-center lg:w-[54%]">
          <HeroGraph />
        </div>
      </div>
    </section>
  );
}
