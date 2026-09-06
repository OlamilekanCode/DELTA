"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";

const cards = [
  {
    tag: "01",
    title: "Historical relationship,\nnot prediction",
    body: "Exposure Scores measure how two assets have moved similarly over 90 days. Past correlation does not guarantee future correlation or equivalent performance.",
    color: "#F4C95D",
    bg: "rgba(244,201,93,0.05)",
    border: "rgba(244,201,93,0.2)",
  },
  {
    tag: "02",
    title: "Correlation\ncan change",
    body: "Market regime shifts, macroeconomic events, and sector rotations can rapidly alter correlations. Synthetic Exposure recalculates scores after each market close.",
    color: "#3D7BFF",
    bg: "rgba(61,123,255,0.05)",
    border: "rgba(61,123,255,0.2)",
  },
  {
    tag: "03",
    title: "Not\ninvestment advice",
    body: "Synthetic Exposure is an analytical tool. Nothing on this platform constitutes financial advice, a recommendation to buy or sell any asset, or a forecast of returns.",
    color: "#FF5D73",
    bg: "rgba(255,93,115,0.05)",
    border: "rgba(255,93,115,0.2)",
  },
];

export default function MethodologySection() {
  const reduced = useReducedMotion();

  return (
    <section className="relative overflow-hidden" aria-labelledby="methodology-heading">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8 lg:py-24">
        {/* Header */}
        <div className="mb-12 grid grid-cols-1 gap-8 lg:grid-cols-2 lg:gap-16">
          <motion.div
            initial={reduced ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <p className="mb-4 font-mono text-xs font-medium uppercase tracking-[0.25em] text-muted">
              Methodology
            </p>
            <h2
              id="methodology-heading"
              className="font-heading font-bold leading-[0.92] text-text"
              style={{ fontSize: "clamp(2.4rem, 5vw, 4rem)" }}
            >
              Transparent<br />by design.
            </h2>
          </motion.div>
          <motion.div
            className="flex items-end gap-6"
            initial={reduced ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <div>
              <p className="max-w-sm font-mono text-sm leading-relaxed text-muted">
                Pearson correlation on 90-day aligned daily log returns. Data: Marketstack + CoinGecko. Recalculated nightly.
              </p>
              <Link
                href="/methodology"
                className="mt-5 inline-flex items-center gap-2 font-mono text-sm font-medium text-violet-light transition-colors hover:text-violet"
              >
                Read the full methodology
                <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              </Link>
            </div>
          </motion.div>
        </div>

        {/* Disclaimer cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {cards.map((card, i) => (
            <motion.article
              key={card.tag}
              className="group relative overflow-hidden rounded-2xl border p-5 transition-colors sm:p-6 lg:p-8"
              style={{ background: card.bg, borderColor: card.border }}
              initial={reduced ? false : { opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              whileHover={{ scale: 1.02 }}
            >
              {/* Tag */}
              <div className="mb-6 flex items-center justify-between">
                <span className="font-mono text-xs" style={{ color: card.color }}>{card.tag}</span>
                <div
                  className="size-2 rounded-full"
                  style={{ background: card.color }}
                  aria-hidden="true"
                />
              </div>

              {/* Title — preserve line breaks */}
              <h3
                className="mb-4 font-heading text-xl font-bold leading-tight text-text"
                style={{ whiteSpace: "pre-line" }}
              >
                {card.title}
              </h3>

              <p className="font-mono text-xs leading-relaxed text-muted">{card.body}</p>

              {/* Accent bottom */}
              <div
                className="absolute bottom-0 left-0 right-0 h-[2px]"
                style={{ background: `linear-gradient(90deg, ${card.color}, transparent)` }}
                aria-hidden="true"
              />
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
