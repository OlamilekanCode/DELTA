"use client";

import { useState } from "react";
import Link from "next/link";
import { previewNodes } from "@/lib/fixtures/nvda-graph";
import type { GraphNode } from "@/lib/types";
import DemoDataBadge from "@/components/shared/DemoDataBadge";
import SectionReveal from "@/components/shared/SectionReveal";

const CATEGORIES = ["All", "AI", "DeFi", "Exchange", "BTC Ecosystem"];

const CATEGORY_COLORS: Record<string, string> = {
  "BTC Ecosystem": "#F7931A",
  "DeFi":          "#3D7BFF",
  "AI":            "#71F79F",
  "Semiconductors": "#6D4AFF",
  "Exchange":      "#F4C95D",
};

function NodeDetail({ node }: { node: GraphNode }) {
  return (
    <div className="rounded-xl border border-white/[0.09] bg-panel2 p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-heading text-base font-semibold text-text">{node.name}</span>
        <span className="font-mono text-xs text-muted">{node.symbol}</span>
      </div>
      <div className="space-y-2 font-mono text-xs">
        <div className="flex justify-between">
          <span className="text-muted">Exposure Score</span>
          <span className="font-bold text-violet">{node.score.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted">Category</span>
          <span className="text-text">{node.category}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted">Price</span>
          <span className="text-text">{node.price}</span>
        </div>
      </div>
      <DemoDataBadge className="mt-3" />
    </div>
  );
}

export default function ExposureGraphPreview() {
  const [activeCategory, setActiveCategory] = useState("All");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  const visibleNodes = previewNodes.filter(
    (n) => activeCategory === "All" || n.category === activeCategory || n.isCenter
  );

  const center = previewNodes.find((n) => n.isCenter)!;

  return (
    <section className="mx-auto max-w-7xl px-6 py-24 lg:px-8" aria-labelledby="graph-preview-heading">
      <SectionReveal>
        <p className="mb-3 font-mono text-xs font-medium uppercase tracking-[0.2em] text-violet">
          Exposure Graph
        </p>
        <h2 id="graph-preview-heading" className="font-heading text-3xl font-bold text-text sm:text-4xl">
          See every connection at once.
        </h2>
        <p className="mt-3 max-w-lg text-base text-muted">
          Click a node to see its Exposure Score, category, and data. Full interactive graph with zoom, pan, and depth controls available on the graph route.
        </p>
      </SectionReveal>

      {/* Filters */}
      <SectionReveal delay={0.05}>
        <div className="mt-8 flex flex-wrap gap-2" role="group" aria-label="Filter by category">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setActiveCategory(cat)}
              aria-pressed={activeCategory === cat}
              className={`rounded-full border px-4 py-1.5 text-xs font-medium transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet ${
                activeCategory === cat
                  ? "border-violet bg-violet/20 text-violet-light"
                  : "border-white/[0.09] bg-panel text-muted hover:border-violet/40 hover:text-text"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </SectionReveal>

      <SectionReveal delay={0.1}>
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* SVG Graph */}
          <div
            className="lg:col-span-2 overflow-hidden rounded-2xl border border-white/[0.09] bg-panel"
            style={{ height: 380 }}
          >
            <svg
              viewBox="0 0 100 100"
              className="h-full w-full"
              role="img"
              aria-label="NVDA Exposure Graph preview — click a node to see details"
            >
              {/* Edges */}
              {visibleNodes.filter((n) => !n.isCenter).map((node) => (
                <line
                  key={node.id}
                  x1={center.x} y1={center.y}
                  x2={node.x}   y2={node.y}
                  stroke={`rgba(109,74,255,${node.score * 0.5})`}
                  strokeWidth={0.15 + node.score * 0.35}
                />
              ))}

              {/* Nodes */}
              {visibleNodes.map((node) => {
                const color = CATEGORY_COLORS[node.category] ?? "#9B7BFF";
                const r = node.isCenter ? 5.5 : 3.2;
                const isSelected = selectedNode?.id === node.id;
                return (
                  <g
                    key={node.id}
                    role="button"
                    tabIndex={0}
                    aria-label={`${node.name} — Exposure Score ${node.score.toFixed(2)}`}
                    onClick={() => setSelectedNode(node)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setSelectedNode(node); }}
                    className="cursor-pointer"
                  >
                    {isSelected && (
                      <circle cx={node.x} cy={node.y} r={r + 2.5} fill="none" stroke="#6D4AFF" strokeWidth="0.6" />
                    )}
                    <circle cx={node.x} cy={node.y} r={r + 1.5} fill={color} opacity={0.12} />
                    <circle cx={node.x} cy={node.y} r={r} fill={node.isCenter ? "#6D4AFF" : color} />
                    <text
                      x={node.x}
                      y={node.isCenter ? node.y + 9 : node.y + r + 3}
                      textAnchor="middle"
                      fontSize={node.isCenter ? 3 : 2.5}
                      fill={node.isCenter ? "#F5F7FF" : "#8E94A7"}
                      fontFamily="var(--font-ibm-plex-mono), monospace"
                      style={{ pointerEvents: "none" }}
                    >
                      {node.symbol}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Detail panel */}
          <div className="flex flex-col gap-4">
            {selectedNode ? (
              <NodeDetail node={selectedNode} />
            ) : (
              <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-white/[0.09] p-6 text-center">
                <p className="text-sm text-muted">Click a node to see its Exposure Score and details</p>
              </div>
            )}

            <Link
              href="/graph/NVDA"
              className="flex items-center justify-center gap-2 rounded-xl border border-violet/40 bg-violet/10 px-4 py-3 text-sm font-medium text-violet-light transition-all hover:border-violet hover:bg-violet/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet"
            >
              View full interactive graph
              <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
            </Link>
          </div>
        </div>
      </SectionReveal>
    </section>
  );
}
