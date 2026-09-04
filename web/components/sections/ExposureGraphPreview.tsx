"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { previewNodes } from "@/lib/fixtures/nvda-graph";
import type { GraphNode } from "@/lib/types";
import DemoDataBadge from "@/components/shared/DemoDataBadge";

const CATEGORIES = ["All", "AI", "DeFi", "Exchange", "BTC Ecosystem"];

const CATEGORY_COLORS: Record<string, string> = {
  "BTC Ecosystem":  "#F7931A",
  "DeFi":           "#3D7BFF",
  "AI":             "#71F79F",
  "Semiconductors": "#6D4AFF",
  "Exchange":       "#F4C95D",
};

function NodeDetail({ node }: { node: GraphNode }) {
  const color = CATEGORY_COLORS[node.category] ?? "#9B7BFF";
  return (
    <motion.div
      className="rounded-2xl border p-5"
      style={{ background: "rgba(255,255,255,0.03)", borderColor: `${color}40` }}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div className="mb-4 flex items-start justify-between gap-2">
        <div>
          <p className="font-heading text-xl font-bold text-text">{node.symbol}</p>
          <p className="font-mono text-xs text-muted">{node.name}</p>
        </div>
        <span
          className="rounded-full border px-2 py-0.5 font-mono text-[10px]"
          style={{ color, borderColor: `${color}40`, background: `${color}12` }}
        >
          {node.category}
        </span>
      </div>

      {/* Big score */}
      <div className="mb-4 rounded-xl p-4" style={{ background: `${color}0A`, border: `1px solid ${color}25` }}>
        <p className="mb-1 font-mono text-[10px] uppercase tracking-widest text-muted">Exposure Score</p>
        <p className="font-heading text-4xl font-bold" style={{ color }}>{node.score.toFixed(2)}</p>
      </div>

      <div className="space-y-2 font-mono text-xs">
        <div className="flex justify-between">
          <span className="text-muted">Price</span>
          <span className="text-text">{node.price}</span>
        </div>
      </div>
      <DemoDataBadge className="mt-3" />
    </motion.div>
  );
}

export default function ExposureGraphPreview() {
  const reduced = useReducedMotion();
  const [activeCategory, setActiveCategory] = useState("All");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const visibleNodes = previewNodes.filter(
    (n) => activeCategory === "All" || n.category === activeCategory || n.isCenter
  );

  const center = previewNodes.find((n) => n.isCenter)!;

  return (
    <section className="relative overflow-hidden" aria-labelledby="graph-preview-heading">
      <div
        className="pointer-events-none absolute inset-0"
        aria-hidden="true"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 70% 50%, rgba(61,123,255,0.05) 0%, transparent 65%)",
        }}
      />

      <div className="relative mx-auto max-w-7xl px-6 py-24 lg:px-8">
        {/* Header */}
        <div className="mb-10 grid grid-cols-1 gap-8 lg:grid-cols-2 lg:gap-16">
          <motion.div
            initial={reduced ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <p className="mb-4 font-mono text-xs font-medium uppercase tracking-[0.25em] text-violet">
              Exposure Graph
            </p>
            <h2
              id="graph-preview-heading"
              className="font-heading font-bold leading-[0.92] text-text"
              style={{ fontSize: "clamp(2.4rem, 5vw, 4rem)" }}
            >
              Every connection<br />
              <span
                style={{
                  background: "linear-gradient(135deg, #9B7BFF 0%, #6D4AFF 60%, #3D7BFF 100%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                at once.
              </span>
            </h2>
          </motion.div>
          <motion.div
            className="flex items-end"
            initial={reduced ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <p className="max-w-sm font-mono text-sm leading-relaxed text-muted">
              Click any node to see its Exposure Score and category. The full interactive graph with zoom and depth controls is one click away.
            </p>
          </motion.div>
        </div>

        {/* Filters */}
        <motion.div
          className="mb-6 flex flex-wrap gap-2"
          role="group"
          aria-label="Filter by category"
          initial={reduced ? false : { opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setActiveCategory(cat)}
              aria-pressed={activeCategory === cat}
              className="rounded-full border px-4 py-1.5 font-mono text-xs font-medium transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet"
              style={
                activeCategory === cat
                  ? { borderColor: "#6D4AFF", background: "rgba(109,74,255,0.2)", color: "#9B7BFF" }
                  : { borderColor: "rgba(255,255,255,0.09)", background: "rgba(11,13,20,1)", color: "#6B7280" }
              }
            >
              {cat}
            </button>
          ))}
        </motion.div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* SVG Graph */}
          <motion.div
            className="lg:col-span-2 overflow-hidden rounded-2xl border border-white/[0.09] bg-panel"
            style={{ height: 400 }}
            initial={reduced ? false : { opacity: 0, scale: 0.98 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.15 }}
          >
            <svg
              viewBox="0 0 100 100"
              className="h-full w-full"
              role="img"
              aria-label="NVDA Exposure Graph preview — click a node to see details"
            >
              <defs>
                <filter id="glow-preview" x="-80%" y="-80%" width="260%" height="260%">
                  <feGaussianBlur stdDeviation="1.2" result="blur" />
                  <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
              </defs>

              {/* Edges */}
              {visibleNodes.filter((n) => !n.isCenter).map((node) => {
                const color = CATEGORY_COLORS[node.category] ?? "#9B7BFF";
                const isHovered = hoveredNode === node.id || hoveredNode === "center";
                return (
                  <motion.line
                    key={node.id}
                    x1={center.x} y1={center.y}
                    x2={node.x}   y2={node.y}
                    stroke={isHovered ? color : `rgba(109,74,255,${node.score * 0.4})`}
                    strokeWidth={isHovered ? 0.5 + node.score * 0.4 : 0.15 + node.score * 0.3}
                    style={{ transition: "stroke 0.2s, stroke-width 0.2s" }}
                  />
                );
              })}

              {/* Nodes */}
              {visibleNodes.map((node, i) => {
                const color = CATEGORY_COLORS[node.category] ?? "#9B7BFF";
                const r = node.isCenter ? 5.5 : 3.2;
                const isSelected = selectedNode?.id === node.id;
                const isHov = hoveredNode === node.id;
                return (
                  <motion.g
                    key={node.id}
                    role="button"
                    tabIndex={0}
                    aria-label={`${node.name} — Exposure Score ${node.score.toFixed(2)}`}
                    onClick={() => setSelectedNode(node)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setSelectedNode(node); }}
                    onMouseEnter={() => setHoveredNode(node.isCenter ? "center" : node.id)}
                    onMouseLeave={() => setHoveredNode(null)}
                    className="cursor-pointer"
                    initial={reduced ? false : { opacity: 0, scale: 0 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.4, delay: 0.2 + i * 0.04, ease: "backOut" }}
                    style={{ transformOrigin: `${node.x}px ${node.y}px` }}
                  >
                    {/* Glow ring on select */}
                    {(isSelected || isHov) && (
                      <circle
                        cx={node.x} cy={node.y} r={r + 2.5}
                        fill="none"
                        stroke={color}
                        strokeWidth="0.5"
                        opacity={0.6}
                      />
                    )}
                    {/* Outer glow */}
                    <circle cx={node.x} cy={node.y} r={r + 1.5} fill={color} opacity={0.1} />
                    {/* Body */}
                    <circle
                      cx={node.x} cy={node.y} r={r}
                      fill={node.isCenter ? "#6D4AFF" : "rgba(11,13,20,0.95)"}
                      stroke={color}
                      strokeWidth={node.isCenter ? 0 : 0.4}
                      filter={node.isCenter ? "url(#glow-preview)" : undefined}
                    />
                    {/* Label */}
                    <text
                      x={node.x}
                      y={node.isCenter ? node.y + 9 : node.y + r + 3}
                      textAnchor="middle"
                      fontSize={node.isCenter ? 3 : 2.5}
                      fill={node.isCenter ? "#fff" : "#8E94A7"}
                      fontFamily="var(--font-ibm-plex-mono), monospace"
                      style={{ pointerEvents: "none" }}
                    >
                      {node.symbol}
                    </text>
                  </motion.g>
                );
              })}
            </svg>
          </motion.div>

          {/* Detail panel */}
          <motion.div
            className="flex flex-col gap-4"
            initial={reduced ? false : { opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            {selectedNode ? (
              <NodeDetail node={selectedNode} />
            ) : (
              <div
                className="flex flex-1 items-center justify-center rounded-2xl border p-8 text-center"
                style={{ borderColor: "rgba(109,74,255,0.15)", background: "rgba(109,74,255,0.03)" }}
              >
                <div>
                  <div className="mb-3 mx-auto size-10 rounded-full bg-violet/10 flex items-center justify-center">
                    <div className="size-2 rounded-full bg-violet" />
                  </div>
                  <p className="font-mono text-xs text-muted">Click a node to see its Exposure Score and details</p>
                </div>
              </div>
            )}

            <Link
              href="/graph/NVDA"
              className="flex items-center justify-center gap-2 rounded-xl border px-4 py-3 font-mono text-sm font-medium transition-all"
              style={{
                borderColor: "rgba(109,74,255,0.35)",
                background: "rgba(109,74,255,0.08)",
                color: "#9B7BFF",
              }}
            >
              View full interactive graph
              <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
            </Link>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
