"use client";

import { useReducedMotion, motion } from "framer-motion";
import DemoDataBadge from "@/components/shared/DemoDataBadge";

interface Node {
  id: string;
  symbol: string;
  score: number;
  x: number;
  y: number;
  category: "center" | "ai" | "semi" | "datacenter" | "correlated" | "defi";
  angle?: number;
}

const NODES: Node[] = [
  // Center
  { id: "nvda", symbol: "NVDA",  score: 1.00, x: 50, y: 50, category: "center" },
  // AI cluster (top-right)
  { id: "rndr", symbol: "RNDR",  score: 0.78, x: 68, y: 18, category: "ai" },
  { id: "akt",  symbol: "AKT",   score: 0.72, x: 76, y: 28, category: "ai" },
  { id: "fet",  symbol: "FET",   score: 0.69, x: 82, y: 40, category: "ai" },
  { id: "agix", symbol: "AGIX",  score: 0.67, x: 80, y: 55, category: "ai" },
  { id: "ocean",symbol: "OCEAN", score: 0.61, x: 73, y: 67, category: "ai" },
  // Semiconductor cluster (top-left)
  { id: "sol",  symbol: "SOL",   score: 0.74, x: 32, y: 18, category: "semi" },
  { id: "avax", symbol: "AVAX",  score: 0.70, x: 22, y: 30, category: "semi" },
  { id: "dot",  symbol: "DOT",   score: 0.63, x: 18, y: 44, category: "semi" },
  // Data center cluster (bottom)
  { id: "link", symbol: "LINK",  score: 0.65, x: 42, y: 82, category: "datacenter" },
  { id: "arb",  symbol: "ARB",   score: 0.60, x: 58, y: 82, category: "datacenter" },
  { id: "op",   symbol: "OP",    score: 0.55, x: 66, y: 74, category: "datacenter" },
  // Correlated / BTC cluster (left)
  { id: "btc",  symbol: "BTC",   score: 0.82, x: 20, y: 58, category: "correlated" },
  { id: "eth",  symbol: "ETH",   score: 0.76, x: 26, y: 70, category: "correlated" },
  { id: "matic",symbol: "MATIC", score: 0.58, x: 35, y: 76, category: "correlated" },
];

const CATEGORY_CONFIG = {
  center:     { color: "#6D4AFF", glow: "rgba(109,74,255,0.5)", r: 7 },
  ai:         { color: "#71F79F", glow: "rgba(113,247,159,0.3)", r: 3.2 },
  semi:       { color: "#9B7BFF", glow: "rgba(155,123,255,0.3)", r: 3.2 },
  datacenter: { color: "#3D7BFF", glow: "rgba(61,123,255,0.3)", r: 3.2 },
  correlated: { color: "#F7931A", glow: "rgba(247,147,26,0.3)", r: 3.4 },
  defi:       { color: "#F4C95D", glow: "rgba(244,201,93,0.3)", r: 3.2 },
} as const;

const CATEGORY_LABELS = [
  { label: "AI TOKENS",            x: 74, y: 12, color: "#71F79F" },
  { label: "SEMICONDUCTOR TOKENS", x: 18, y: 12, color: "#9B7BFF" },
  { label: "DATA CENTER TOKENS",   x: 50, y: 90, color: "#3D7BFF" },
  { label: "CORRELATED ASSETS",    x: 18, y: 76, color: "#F7931A" },
];

export default function HeroGraph() {
  const reduced = useReducedMotion();

  return (
    <div className="relative w-full select-none" style={{ aspectRatio: "1 / 1", maxWidth: 520 }}>
      <svg
        viewBox="0 0 100 100"
        className="h-full w-full"
        role="img"
        aria-label="NVDA Exposure Graph — interactive network of correlated crypto assets"
      >
        {/* Glow filter */}
        <defs>
          <filter id="glow-violet" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="1.5" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="glow-node" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="0.8" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <radialGradient id="bg-glow" cx="50%" cy="50%">
            <stop offset="0%" stopColor="rgba(109,74,255,0.08)" />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
        </defs>

        {/* Background glow circle */}
        <circle cx="50" cy="50" r="48" fill="url(#bg-glow)" />

        {/* Concentric rings */}
        {[15, 28, 42].map((r) => (
          <circle key={r} cx="50" cy="50" r={r} fill="none"
            stroke="rgba(109,74,255,0.07)" strokeWidth="0.3" strokeDasharray="1 2" />
        ))}

        {/* Category label dots (floating) */}
        {CATEGORY_LABELS.map((cl) => (
          <text
            key={cl.label}
            x={cl.x} y={cl.y}
            textAnchor="middle"
            fontSize="2.1"
            fill={cl.color}
            opacity={0.7}
            fontFamily="var(--font-ibm-plex-mono), monospace"
            letterSpacing="0.05"
          >
            {cl.label}
          </text>
        ))}

        {/* Edges */}
        {NODES.filter((n) => n.category !== "center").map((node, i) => {
          const center = NODES[0]!;
          const cfg = CATEGORY_CONFIG[node.category];
          const opacity = 0.15 + node.score * 0.45;
          const strokeW = 0.12 + node.score * 0.25;
          return (
            <motion.line
              key={node.id}
              x1={center.x} y1={center.y}
              x2={node.x} y2={node.y}
              stroke={cfg.color}
              strokeWidth={strokeW}
              strokeOpacity={opacity}
              initial={reduced ? false : { pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.2 + i * 0.05, ease: "easeOut" }}
            />
          );
        })}

        {/* Nodes */}
        {NODES.map((node, i) => {
          const cfg = CATEGORY_CONFIG[node.category];
          const isCenter = node.category === "center";
          return (
            <motion.g
              key={node.id}
              initial={reduced ? false : { opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, delay: isCenter ? 0 : 0.15 + i * 0.06, ease: "backOut" }}
              style={{ transformOrigin: `${node.x}px ${node.y}px` }}
            >
              {/* Outer glow ring */}
              <circle cx={node.x} cy={node.y} r={cfg.r + 2.5} fill={cfg.color} opacity={0.08} />
              {/* Node body */}
              <circle
                cx={node.x} cy={node.y} r={cfg.r}
                fill={isCenter ? "#6D4AFF" : "rgba(11,13,20,0.9)"}
                stroke={cfg.color}
                strokeWidth={isCenter ? 0 : 0.4}
                filter={isCenter ? "url(#glow-violet)" : undefined}
              />
              {/* Center pulse */}
              {isCenter && !reduced && (
                <>
                  <motion.circle cx={node.x} cy={node.y} r={cfg.r + 1.5}
                    fill="none" stroke="#6D4AFF" strokeWidth="0.5"
                    animate={{ r: [cfg.r + 1.5, cfg.r + 5], opacity: [0.7, 0] }}
                    transition={{ duration: 2.5, repeat: Infinity, ease: "easeOut" }} />
                  <motion.circle cx={node.x} cy={node.y} r={cfg.r + 1.5}
                    fill="none" stroke="#9B7BFF" strokeWidth="0.3"
                    animate={{ r: [cfg.r + 1.5, cfg.r + 8], opacity: [0.4, 0] }}
                    transition={{ duration: 2.5, repeat: Infinity, ease: "easeOut", delay: 0.8 }} />
                </>
              )}
              {/* Ticker label */}
              <text
                x={node.x} y={node.y + (isCenter ? 0.8 : 0.8)}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={isCenter ? 3.5 : 2.4}
                fontWeight={isCenter ? "700" : "400"}
                fill={isCenter ? "#fff" : cfg.color}
                fontFamily="var(--font-ibm-plex-mono), monospace"
                style={{ pointerEvents: "none" }}
              >
                {node.symbol}
              </text>
              {/* Score badge on non-center nodes */}
              {!isCenter && (
                <text
                  x={node.x} y={node.y + cfg.r + 2.5}
                  textAnchor="middle"
                  fontSize="1.8"
                  fill="rgba(255,255,255,0.4)"
                  fontFamily="var(--font-ibm-plex-mono), monospace"
                  style={{ pointerEvents: "none" }}
                >
                  {node.score.toFixed(2)}
                </text>
              )}
            </motion.g>
          );
        })}
      </svg>

      <div className="absolute bottom-2 right-2">
        <DemoDataBadge />
      </div>
    </div>
  );
}
