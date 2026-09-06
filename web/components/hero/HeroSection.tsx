"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";

const HeroGraph = dynamic(() => import("./HeroGraph"), {
  ssr: false,
  loading: () => (
    <div
      className="w-full rounded-2xl border"
      style={{
        maxWidth: 600,
        aspectRatio: "1 / 0.85",
        borderColor: "rgba(109,74,255,0.2)",
        background: "rgba(8,11,18,0.9)",
      }}
      aria-label="Loading Analysis Terminal"
    />
  ),
});

const bullets = [
  {
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="size-4" aria-hidden="true">
        <path fillRule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 0l-2 2a1 1 0 101.414 1.414L8 10.414l1.293 1.293a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
      </svg>
    ),
    title: "Cross-Market Exposure",
    body: "Any stock ↔ full crypto universe",
  },
  {
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="size-4" aria-hidden="true">
        <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
      </svg>
    ),
    title: "Pearson Correlation",
    body: "90-day on aligned daily returns",
  },
  {
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="size-4" aria-hidden="true">
        <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
      </svg>
    ),
    title: "Portfolio Insights",
    body: "Wallet-level exposure analysis",
  },
];

export default function HeroSection() {
  const reduced = useReducedMotion();
  const sectionRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ["start start", "end start"] });
  const copyY = useTransform(scrollYProgress, [0, 1], ["0%", "20%"]);
  const copyOpacity = useTransform(scrollYProgress, [0, 0.6], [1, 0]);
  const graphY = useTransform(scrollYProgress, [0, 1], ["0%", "10%"]);

  return (
    <section
      ref={sectionRef}
      className="relative flex flex-col overflow-hidden"
      style={{ minHeight: "100svh" }}
      aria-labelledby="hero-heading"
    >
      {/* Dot grid texture */}
      <div
        className="pointer-events-none absolute inset-0"
        aria-hidden="true"
        style={{
          backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.055) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
          opacity: 0.6,
        }}
      />

      {/* Right radial glow */}
      <div
        className="pointer-events-none absolute right-0 top-0 h-full w-2/3"
        aria-hidden="true"
        style={{
          background:
            "radial-gradient(ellipse 70% 80% at 75% 40%, rgba(109,74,255,0.14) 0%, rgba(61,123,255,0.06) 45%, transparent 70%)",
        }}
      />

      {/* Bottom fade */}
      <div
        className="pointer-events-none absolute bottom-0 inset-x-0 h-40"
        aria-hidden="true"
        style={{ background: "linear-gradient(to bottom, transparent, #030508)" }}
      />

      <div className="relative mx-auto flex flex-1 flex-col justify-center max-w-7xl w-full px-4 pt-24 pb-12 sm:px-6 sm:pt-28 sm:pb-16 lg:px-8 lg:pt-32">
        <div className="grid grid-cols-1 gap-8 sm:gap-10 lg:grid-cols-[44%_56%] lg:gap-8 lg:items-center">

          {/* ── Left: Copy ── */}
          <motion.div
            className="flex flex-col items-start"
            style={reduced ? {} : { y: copyY, opacity: copyOpacity }}
          >
            {/* Eyebrow */}
            <motion.div
              className="mb-7 flex items-center gap-2"
              initial={reduced ? false : { opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <motion.span
                className="inline-block size-2 rounded-full bg-green"
                animate={reduced ? {} : { opacity: [1, 0.4, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
                aria-hidden="true"
              />
              <p className="font-mono text-xs font-medium uppercase tracking-[0.28em] text-muted">
                The Stock ↔ Crypto Exposure Layer
              </p>
            </motion.div>

            {/* Heading */}
            <motion.h1
              id="hero-heading"
              className="font-heading font-bold leading-[0.95] text-text"
              style={{ fontSize: "clamp(3.2rem, 7.5vw, 6rem)" }}
              initial={reduced ? false : { opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.05 }}
            >
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
              the<br />Market.
            </motion.h1>

            {/* Body */}
            <motion.p
              className="mt-6 w-full max-w-sm text-[1.05rem] leading-relaxed text-muted"
              initial={reduced ? false : { opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.15 }}
            >
              Synthetic Exposure reveals how any stock moves with the crypto market — using 90-day historical correlation across thousands of aligned observations.
            </motion.p>

            {/* Bullets */}
            <motion.ul
              className="mt-8 space-y-3"
              role="list"
              initial={reduced ? false : { opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.22 }}
            >
              {bullets.map((b) => (
                <li key={b.title} className="flex items-center gap-3">
                  <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-violet/15 text-violet-light">
                    {b.icon}
                  </span>
                  <div>
                    <span className="text-sm font-semibold text-text">{b.title}</span>
                    <span className="ml-2 font-mono text-[13px] text-muted">{b.body}</span>
                  </div>
                </li>
              ))}
            </motion.ul>

            {/* CTAs */}
            <motion.div
              className="mt-10 flex flex-wrap items-center gap-2 sm:gap-3"
              initial={reduced ? false : { opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
            >
              <Link
                href="/#nvda-example"
                className="inline-flex items-center gap-2 rounded-xl px-6 py-3.5 text-sm font-bold text-white transition-all active:scale-95"
                style={{
                  background: "linear-gradient(135deg, #6D4AFF 0%, #4F35CC 100%)",
                  boxShadow: "0 0 32px rgba(109,74,255,0.4), inset 0 1px 0 rgba(255,255,255,0.12)",
                }}
              >
                Explore NVDA
                <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              </Link>

              <Link
                href="/portfolio"
                className="inline-flex items-center gap-2 rounded-xl border border-white/[0.12] bg-white/[0.04] px-6 py-3.5 text-sm font-semibold text-text backdrop-blur-sm transition-all hover:border-violet/40 hover:bg-white/[0.07] active:scale-95"
              >
                Connect wallet
              </Link>
            </motion.div>

            {/* Disclaimer */}
            <motion.p
              className="mt-7 font-mono text-[11px] uppercase tracking-widest text-muted"
              style={{ textShadow: "0 0 12px rgba(109,74,255,0.5), 0 1px 3px rgba(0,0,0,0.8)" }}
              initial={reduced ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.45 }}
            >
              Analytical tool · Historical data only · Not financial advice
            </motion.p>
          </motion.div>

          {/* ── Right: Terminal Graph ── */}
          <motion.div
            className="flex w-full items-center justify-center lg:justify-end"
            style={reduced ? {} : { y: graphY }}
            initial={reduced ? false : { opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          >
            <HeroGraph />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
