"use client";

import { motion, useReducedMotion } from "framer-motion";

// Inner ring r=38 from center (100,100)
const INNER = [
  { id: "btc",  symbol: "BTC",  score: 0.82, x: 138, y: 100, color: "#F7931A", cat: "BTC" },
  { id: "eth",  symbol: "ETH",  score: 0.76, x: 100, y: 138, color: "#3D7BFF", cat: "DeFi" },
  { id: "sol",  symbol: "SOL",  score: 0.74, x: 62,  y: 100, color: "#9B7BFF", cat: "L1" },
  { id: "rndr", symbol: "RNDR", score: 0.78, x: 100, y: 62,  color: "#71F79F", cat: "AI" },
];

// Outer ring r=65 from center, 45° intervals starting 22.5°
const OUTER = [
  { id: "akt",   symbol: "AKT",  score: 0.72, x: 160, y: 125, color: "#71F79F", cat: "AI",    lx: 170, ly: 125, la: "start" },
  { id: "fet",   symbol: "FET",  score: 0.69, x: 125, y: 160, color: "#71F79F", cat: "AI",    lx: 125, ly: 172, la: "middle" },
  { id: "link",  symbol: "LINK", score: 0.65, x: 75,  y: 160, color: "#3D7BFF", cat: "DeFi",  lx: 75,  ly: 172, la: "middle" },
  { id: "avax",  symbol: "AVAX", score: 0.70, x: 40,  y: 125, color: "#9B7BFF", cat: "L1",    lx: 30,  ly: 125, la: "end" },
  { id: "dot",   symbol: "DOT",  score: 0.63, x: 40,  y: 75,  color: "#9B7BFF", cat: "L1",    lx: 30,  ly: 75,  la: "end" },
  { id: "agix",  symbol: "AGIX", score: 0.67, x: 75,  y: 40,  color: "#71F79F", cat: "AI",    lx: 75,  ly: 28,  la: "middle" },
  { id: "arb",   symbol: "ARB",  score: 0.60, x: 125, y: 40,  color: "#6D4AFF", cat: "L2",    lx: 125, ly: 28,  la: "middle" },
  { id: "ocn",   symbol: "OCN",  score: 0.61, x: 160, y: 75,  color: "#71F79F", cat: "AI",    lx: 170, ly: 75,  la: "start" },
];

const ALL_NODES = [...INNER, ...OUTER];

const SCORES = [
  { symbol: "BTC",  score: 0.82, color: "#F7931A" },
  { symbol: "RNDR", score: 0.78, color: "#71F79F" },
  { symbol: "ETH",  score: 0.76, color: "#3D7BFF" },
  { symbol: "SOL",  score: 0.74, color: "#9B7BFF" },
  { symbol: "AKT",  score: 0.72, color: "#71F79F" },
  { symbol: "AVAX", score: 0.70, color: "#9B7BFF" },
];

const CATS = [
  { label: "AI", color: "#71F79F" },
  { label: "BTC ECOSYSTEM", color: "#F7931A" },
  { label: "L1 NETWORKS", color: "#9B7BFF" },
  { label: "DEFI", color: "#3D7BFF" },
];

export default function HeroGraph() {
  const reduced = useReducedMotion();

  return (
    <div
      className="w-full select-none"
      style={{ maxWidth: 600 }}
      aria-label="Synthetic Exposure Analysis Terminal — interactive exposure graph"
    >
      {/* Terminal window */}
      <div
        className="overflow-hidden rounded-2xl border"
        style={{
          background: "linear-gradient(135deg, #0A0C18 0%, #060810 100%)",
          borderColor: "rgba(109,74,255,0.25)",
          boxShadow: "0 0 60px rgba(109,74,255,0.12), 0 0 120px rgba(61,123,255,0.06), inset 0 1px 0 rgba(255,255,255,0.04)",
        }}
      >
        {/* Terminal header */}
        <div
          className="flex items-center gap-3 border-b px-4 py-2.5"
          style={{ borderColor: "rgba(109,74,255,0.15)", background: "rgba(109,74,255,0.04)" }}
        >
          <div className="flex items-center gap-1.5">
            <div className="size-3 rounded-full" style={{ background: "#FF5D73", opacity: 0.8 }} />
            <div className="size-3 rounded-full" style={{ background: "#F4C95D", opacity: 0.8 }} />
            <div className="size-3 rounded-full" style={{ background: "#71F79F", opacity: 0.8 }} />
          </div>
          <span className="flex-1 text-center font-mono text-xs uppercase tracking-[0.18em] text-muted">
            Synthetic Exposure ANALYSIS ENGINE
          </span>
          <div className="flex items-center gap-1.5">
            <motion.div
              className="size-1.5 rounded-full"
              style={{ background: "#71F79F" }}
              animate={reduced ? {} : { opacity: [1, 0.3, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            <span className="font-mono text-[11px] text-green">ACTIVE</span>
          </div>
        </div>

        {/* Main content */}
        <div className="flex">
          {/* Graph area */}
          <div className="relative flex-1">
            <svg viewBox="0 0 200 200" className="h-full w-full" style={{ minHeight: 220 }} aria-hidden="true">
              <defs>
                <filter id="hg-glow" x="-80%" y="-80%" width="260%" height="260%">
                  <feGaussianBlur stdDeviation="1.8" result="blur" />
                  <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
                <filter id="hg-glow-sm" x="-60%" y="-60%" width="220%" height="220%">
                  <feGaussianBlur stdDeviation="0.8" result="blur" />
                  <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
                <radialGradient id="hg-center-grad" cx="50%" cy="50%">
                  <stop offset="0%" stopColor="#6D4AFF" />
                  <stop offset="100%" stopColor="#4A2FCC" />
                </radialGradient>
              </defs>

              {/* Concentric rings */}
              {[20, 38, 65].map((r) => (
                <circle
                  key={r}
                  cx="100" cy="100" r={r}
                  fill="none"
                  stroke="rgba(109,74,255,0.08)"
                  strokeWidth="0.4"
                  strokeDasharray={r < 38 ? "1.5 3" : "1 4"}
                />
              ))}

              {/* Edges — outer ring */}
              {OUTER.map((node, i) => (
                <motion.line
                  key={node.id}
                  x1="100" y1="100" x2={node.x} y2={node.y}
                  stroke={node.color}
                  strokeWidth={0.2 + node.score * 0.3}
                  strokeOpacity={0.2 + node.score * 0.3}
                  initial={reduced ? false : { pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.6 + i * 0.06, ease: "easeOut" }}
                />
              ))}

              {/* Edges — inner ring */}
              {INNER.map((node, i) => (
                <motion.line
                  key={node.id}
                  x1="100" y1="100" x2={node.x} y2={node.y}
                  stroke={node.color}
                  strokeWidth={0.4 + node.score * 0.4}
                  strokeOpacity={0.35 + node.score * 0.3}
                  initial={reduced ? false : { pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 1 }}
                  transition={{ duration: 0.5, delay: 0.3 + i * 0.07, ease: "easeOut" }}
                />
              ))}

              {/* Outer ring nodes */}
              {OUTER.map((node, i) => (
                <motion.g
                  key={node.id}
                  initial={reduced ? false : { opacity: 0, scale: 0 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.35, delay: 0.7 + i * 0.05, ease: "backOut" }}
                  style={{ transformOrigin: `${node.x}px ${node.y}px` }}
                >
                  {/* Glow halo */}
                  <circle cx={node.x} cy={node.y} r={7} fill={node.color} opacity={0.06} />
                  {/* Node body */}
                  <circle
                    cx={node.x} cy={node.y} r={5}
                    fill="rgba(8,11,18,0.95)"
                    stroke={node.color}
                    strokeWidth="0.6"
                    filter="url(#hg-glow-sm)"
                  />
                  {/* Ticker inside */}
                  <text
                    x={node.x} y={node.y + 1.5}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="3.2"
                    fontWeight="600"
                    fill={node.color}
                    fontFamily="var(--font-ibm-plex-mono), monospace"
                    style={{ pointerEvents: "none" }}
                  >
                    {node.symbol}
                  </text>
                  {/* Score label outside */}
                  <text
                    x={node.lx} y={node.ly + 1.5}
                    textAnchor={node.la as "start" | "middle" | "end"}
                    dominantBaseline="middle"
                    fontSize="3.5"
                    fill="rgba(255,255,255,0.35)"
                    fontFamily="var(--font-ibm-plex-mono), monospace"
                    style={{ pointerEvents: "none" }}
                  >
                    {node.score.toFixed(2)}
                  </text>
                </motion.g>
              ))}

              {/* Inner ring nodes */}
              {INNER.map((node, i) => (
                <motion.g
                  key={node.id}
                  initial={reduced ? false : { opacity: 0, scale: 0 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.4, delay: 0.4 + i * 0.07, ease: "backOut" }}
                  style={{ transformOrigin: `${node.x}px ${node.y}px` }}
                >
                  <circle cx={node.x} cy={node.y} r={10} fill={node.color} opacity={0.06} />
                  <circle
                    cx={node.x} cy={node.y} r={7}
                    fill="rgba(8,11,18,0.92)"
                    stroke={node.color}
                    strokeWidth="0.8"
                    filter="url(#hg-glow-sm)"
                  />
                  <text
                    x={node.x} y={node.y + 1.5}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="4"
                    fontWeight="700"
                    fill={node.color}
                    fontFamily="var(--font-ibm-plex-mono), monospace"
                    style={{ pointerEvents: "none" }}
                  >
                    {node.symbol}
                  </text>
                </motion.g>
              ))}

              {/* Center: STOCKS node */}
              <motion.g
                initial={reduced ? false : { opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, delay: 0.1, ease: "backOut" }}
                style={{ transformOrigin: "100px 100px" }}
              >
                {/* Pulse rings */}
                {!reduced && (
                  <>
                    <motion.circle cx="100" cy="100" r="14"
                      fill="none" stroke="#6D4AFF" strokeWidth="0.6"
                      animate={{ r: [14, 22], opacity: [0.6, 0] }}
                      transition={{ duration: 2.8, repeat: Infinity, ease: "easeOut" }}
                    />
                    <motion.circle cx="100" cy="100" r="14"
                      fill="none" stroke="#9B7BFF" strokeWidth="0.4"
                      animate={{ r: [14, 30], opacity: [0.4, 0] }}
                      transition={{ duration: 2.8, repeat: Infinity, ease: "easeOut", delay: 1.0 }}
                    />
                  </>
                )}
                {/* Glow bg */}
                <circle cx="100" cy="100" r="16" fill="#6D4AFF" opacity="0.12" filter="url(#hg-glow)" />
                {/* Body */}
                <circle cx="100" cy="100" r="12" fill="url(#hg-center-grad)" filter="url(#hg-glow)" />
                {/* Label */}
                <text
                  x="100" y="98"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="4.5"
                  fontWeight="700"
                  fill="#ffffff"
                  fontFamily="var(--font-ibm-plex-mono), monospace"
                  style={{ pointerEvents: "none" }}
                >
                  STOCKS
                </text>
                <text
                  x="100" y="104"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="2.8"
                  fill="rgba(255,255,255,0.5)"
                  fontFamily="var(--font-ibm-plex-mono), monospace"
                  style={{ pointerEvents: "none" }}
                >
                  any ticker
                </text>
              </motion.g>
            </svg>
          </div>

          {/* Scores panel */}
          <div
            className="hidden w-[148px] shrink-0 border-l sm:flex flex-col p-4"
            style={{ borderColor: "rgba(109,74,255,0.12)" }}
          >
            <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
              Top Scores
            </p>
            <div className="space-y-3">
              {SCORES.map((s, i) => (
                <motion.div
                  key={s.symbol}
                  initial={reduced ? false : { opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.35, delay: 0.8 + i * 0.07 }}
                >
                  <div className="mb-1 flex items-center justify-between">
                    <span className="font-mono text-xs font-semibold text-text">{s.symbol}</span>
                    <span className="font-mono text-xs" style={{ color: s.color }}>
                      {s.score.toFixed(2)}
                    </span>
                  </div>
                  {/* Score bar */}
                  <div
                    className="h-[2px] overflow-hidden rounded-full"
                    style={{ background: "rgba(255,255,255,0.06)" }}
                  >
                    <motion.div
                      className="h-full rounded-full"
                      style={{ background: s.color }}
                      initial={{ width: 0 }}
                      animate={{ width: `${s.score * 100}%` }}
                      transition={reduced ? { duration: 0 } : { duration: 0.8, delay: 0.9 + i * 0.07, ease: "easeOut" }}
                    />
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Category legend */}
            <div className="mt-auto border-t pt-3 space-y-1.5" style={{ borderColor: "rgba(109,74,255,0.12)" }}>
              {CATS.map((c) => (
                <div key={c.label} className="flex items-center gap-1.5">
                  <div className="size-1.5 shrink-0 rounded-full" style={{ background: c.color }} />
                  <span className="font-mono text-[10px] text-muted leading-none">{c.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer bar */}
        <div
          className="flex items-center justify-between border-t px-4 py-2"
          style={{ borderColor: "rgba(109,74,255,0.12)", background: "rgba(109,74,255,0.03)" }}
        >
          <div className="flex items-center gap-3">
            {ALL_NODES.slice(0, 4).map((n) => (
              <span key={n.id} className="font-mono text-[10px]" style={{ color: n.color }}>
                {n.symbol} {n.score.toFixed(2)}
              </span>
            ))}
          </div>
          <span className="font-mono text-[10px] text-muted">
            {ALL_NODES.length} assets mapped
          </span>
        </div>
      </div>
    </div>
  );
}
