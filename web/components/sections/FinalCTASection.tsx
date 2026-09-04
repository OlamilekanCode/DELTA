"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";

export default function FinalCTASection() {
  const reduced = useReducedMotion();

  return (
    <section
      className="relative overflow-hidden"
      aria-labelledby="cta-heading"
      style={{ background: "linear-gradient(135deg, #1A0A4A 0%, #0F062E 40%, #0A0420 100%)" }}
    >
      {/* Grid overlay */}
      <div
        className="pointer-events-none absolute inset-0"
        aria-hidden="true"
        style={{
          backgroundImage:
            "linear-gradient(rgba(109,74,255,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(109,74,255,0.06) 1px, transparent 1px)",
          backgroundSize: "56px 56px",
        }}
      />

      {/* Radial glow center */}
      <div
        className="pointer-events-none absolute inset-0"
        aria-hidden="true"
        style={{
          background:
            "radial-gradient(ellipse 70% 80% at 50% 50%, rgba(109,74,255,0.2) 0%, transparent 65%)",
        }}
      />

      {/* Top border */}
      <div
        className="absolute inset-x-0 top-0 h-px"
        aria-hidden="true"
        style={{ background: "linear-gradient(90deg, transparent, rgba(155,123,255,0.6), transparent)" }}
      />

      <div className="relative mx-auto max-w-7xl px-6 py-32 lg:px-8">
        <div className="flex flex-col items-start">
          {/* Eyebrow */}
          <motion.p
            className="mb-6 font-mono text-xs font-medium uppercase tracking-[0.3em] text-violet-light"
            initial={reduced ? false : { opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            Start now — free
          </motion.p>

          {/* Big heading */}
          <motion.h2
            id="cta-heading"
            className="font-heading font-bold leading-[0.9] text-white"
            style={{ fontSize: "clamp(3rem, 9vw, 7rem)" }}
            initial={reduced ? false : { opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, delay: 0.05 }}
          >
            Map the<br />market today.
          </motion.h2>

          {/* Subtext */}
          <motion.p
            className="mt-8 max-w-md font-mono text-base leading-relaxed text-white/50"
            initial={reduced ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.15 }}
          >
            Explore the free NVDA example, then connect your wallet to unlock the full platform.
          </motion.p>

          {/* CTAs */}
          <motion.div
            className="mt-10 flex flex-wrap items-center gap-4"
            initial={reduced ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <Link
              href="/asset/NVDA"
              className="inline-flex items-center gap-2 rounded-xl bg-white px-8 py-4 text-base font-bold text-bg transition-all hover:bg-white/90 active:scale-95"
            >
              Explore NVDA
              <svg className="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
            </Link>

            <Link
              href="/methodology"
              className="inline-flex items-center gap-2 rounded-xl border border-white/20 bg-white/[0.06] px-8 py-4 text-base font-semibold text-white backdrop-blur-sm transition-all hover:border-white/40 hover:bg-white/[0.1] active:scale-95"
            >
              How it works
            </Link>
          </motion.div>
        </div>

        {/* Disclaimer row */}
        <motion.p
          className="mt-20 font-mono text-[10px] uppercase tracking-widest text-white/25"
          initial={reduced ? false : { opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          Analytical tool · Historical data only · Not financial advice
        </motion.p>
      </div>
    </section>
  );
}
