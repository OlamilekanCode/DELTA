"use client";

import { useReducedMotion, motion } from "framer-motion";
import { heroNodes, heroEdges } from "@/lib/fixtures/nvda-graph";
import DemoDataBadge from "@/components/shared/DemoDataBadge";

const CATEGORY_COLORS: Record<string, string> = {
  "BTC Ecosystem": "#F7931A",
  "DeFi":          "#3D7BFF",
  "AI":            "#71F79F",
  "Semiconductors": "#6D4AFF",
};

export default function HeroGraph() {
  const reduced = useReducedMotion();

  return (
    <div className="relative w-full" style={{ aspectRatio: "1 / 1", maxWidth: 480 }}>
      <svg
        viewBox="0 0 100 100"
        className="h-full w-full"
        role="img"
        aria-label="Interactive NVDA Exposure Graph — showing connected crypto assets"
      >
        {/* Subtle grid rings */}
        {[18, 34, 46].map((r) => (
          <circle key={r} cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="0.4" />
        ))}

        {/* Edges */}
        {heroEdges.map((edge, i) => {
          const from = heroNodes.find((n) => n.id === edge.from)!;
          const to   = heroNodes.find((n) => n.id === edge.to)!;
          const strokeW = 0.18 + edge.weight * 0.3;
          return (
            <motion.line
              key={edge.to}
              x1={from.x} y1={from.y}
              x2={to.x}   y2={to.y}
              stroke={`rgba(109,74,255,${edge.weight * 0.6})`}
              strokeWidth={strokeW}
              initial={reduced ? false : { pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 0.7, delay: 0.3 + i * 0.08, ease: "easeOut" }}
            />
          );
        })}

        {/* Nodes */}
        {heroNodes.map((node, i) => {
          const color = CATEGORY_COLORS[node.category] ?? "#9B7BFF";
          const r = node.isCenter ? 6 : 3.5;
          return (
            <motion.g
              key={node.id}
              initial={reduced ? false : { opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.45, delay: node.isCenter ? 0 : 0.2 + i * 0.07, ease: "backOut" }}
              style={{ transformOrigin: `${node.x}px ${node.y}px` }}
            >
              {/* Glow */}
              <circle cx={node.x} cy={node.y} r={r + 2} fill={color} opacity={0.12} />
              {/* Node */}
              <circle cx={node.x} cy={node.y} r={r} fill={node.isCenter ? "#6D4AFF" : color} />
              {/* Center pulse */}
              {node.isCenter && !reduced && (
                <motion.circle
                  cx={node.x} cy={node.y} r={r + 1}
                  fill="none" stroke="#6D4AFF" strokeWidth="0.5"
                  animate={{ r: [r + 1, r + 4], opacity: [0.6, 0] }}
                  transition={{ duration: 2, repeat: Infinity, ease: "easeOut" }}
                />
              )}
              {/* Label */}
              <text
                x={node.x}
                y={node.isCenter ? node.y + 10 : node.y + r + 3}
                textAnchor="middle"
                fontSize={node.isCenter ? 3.5 : 2.8}
                fill={node.isCenter ? "#F5F7FF" : "#8E94A7"}
                fontFamily="var(--font-ibm-plex-mono), monospace"
              >
                {node.symbol}
              </text>
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
