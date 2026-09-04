"use client";

import Link from "next/link";
import dynamic from "next/dynamic";

const HeroGraph = dynamic(() => import("./HeroGraph"), {
  ssr: false,
  loading: () => (
    <div
      className="w-full rounded-2xl border border-white/[0.09] bg-panel"
      style={{ aspectRatio: "1 / 1", maxWidth: 480 }}
      aria-label="Loading Exposure Graph"
    />
  ),
});

export default function HeroSection() {
  return (
    <section
      className="relative dot-grid min-h-screen pt-24 pb-16 flex items-center"
      aria-labelledby="hero-heading"
    >
      {/* Radial violet glow */}
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
        aria-hidden="true"
        style={{
          width: "80vw",
          height: "80vw",
          maxWidth: 900,
          background: "radial-gradient(ellipse at center, rgba(109,74,255,0.10) 0%, transparent 70%)",
        }}
      />

      <div className="relative mx-auto w-full max-w-7xl px-6 lg:px-8">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
          {/* Copy */}
          <div className="flex flex-col items-start">
            <p className="mb-4 font-mono text-xs font-medium uppercase tracking-[0.2em] text-violet-light">
              THE STOCK ↔ CRYPTO EXPOSURE LAYER
            </p>

            <h1
              id="hero-heading"
              className="font-heading text-5xl font-bold leading-[1.05] text-text sm:text-6xl lg:text-7xl"
            >
              Map the<br />Market.
            </h1>

            <p className="mt-6 max-w-md text-lg leading-relaxed text-muted">
              DELTA maps how stocks and crypto move together using historical market
              data. Discover which crypto assets have historically tracked NVDA, TSLA,
              COIN, and more.
            </p>

            <div className="mt-10 flex flex-wrap items-center gap-4">
              <Link
                href="/asset/NVDA"
                className="inline-flex items-center gap-2 rounded-lg bg-violet px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-violet/25 transition-all hover:bg-violet-light hover:shadow-violet/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet active:scale-95"
              >
                Explore NVDA
                <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              </Link>

              <Link
                href="/portfolio"
                className="inline-flex items-center gap-2 rounded-lg border border-white/[0.09] bg-panel px-6 py-3 text-sm font-semibold text-text transition-all hover:border-violet/50 hover:bg-panel2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet active:scale-95"
              >
                Connect wallet
              </Link>
            </div>
          </div>

          {/* Graph */}
          <div className="flex justify-center lg:justify-end">
            <HeroGraph />
          </div>
        </div>
      </div>
    </section>
  );
}
