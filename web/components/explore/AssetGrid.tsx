"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { ApiAsset } from "@/lib/types";

const CATEGORY_COLORS: Record<string, { text: string; bg: string; border: string }> = {
  "Layer 1":     { text: "#F4C95D", bg: "rgba(244,201,93,0.08)",  border: "rgba(244,201,93,0.25)" },
  "Layer 2":     { text: "#3D7BFF", bg: "rgba(61,123,255,0.08)",  border: "rgba(61,123,255,0.25)" },
  "DeFi":        { text: "#9B7BFF", bg: "rgba(155,123,255,0.08)", border: "rgba(155,123,255,0.25)" },
  "Oracle/Data": { text: "#38BDF8", bg: "rgba(56,189,248,0.08)",  border: "rgba(56,189,248,0.25)" },
  "AI/Compute":  { text: "#71F79F", bg: "rgba(113,247,159,0.08)", border: "rgba(113,247,159,0.25)" },
  "Storage":     { text: "#FB923C", bg: "rgba(251,146,60,0.08)",  border: "rgba(251,146,60,0.25)" },
  "Memecoin":    { text: "#F472B6", bg: "rgba(244,114,182,0.08)", border: "rgba(244,114,182,0.25)" },
  "Technology":  { text: "#9B7BFF", bg: "rgba(155,123,255,0.08)", border: "rgba(155,123,255,0.25)" },
  "Finance":     { text: "#2DD4BF", bg: "rgba(45,212,191,0.08)",  border: "rgba(45,212,191,0.25)" },
};

const DEFAULT_COLOR = { text: "#9B7BFF", bg: "rgba(155,123,255,0.08)", border: "rgba(155,123,255,0.25)" };

function formatPrice(price: number): string {
  if (price < 0.0001) return price.toFixed(8);
  if (price < 0.01)   return price.toFixed(6);
  if (price < 1)      return price.toFixed(4);
  if (price < 100)    return price.toFixed(2);
  return price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function CategoryBadge({ category }: { category: string }) {
  const c = CATEGORY_COLORS[category] ?? DEFAULT_COLOR;
  return (
    <span
      className="rounded-full px-1.5 py-0.5 font-mono text-[10px] font-medium"
      style={{ color: c.text, background: c.bg, border: `1px solid ${c.border}` }}
    >
      {category}
    </span>
  );
}

function Change24h({ pct }: { pct: number }) {
  const positive = pct >= 0;
  return (
    <span
      className={`font-mono text-[10px] font-medium ${positive ? "text-green" : "text-red-400"}`}
    >
      {positive ? "+" : ""}{pct.toFixed(2)}%
    </span>
  );
}

function AssetCard({ asset }: { asset: ApiAsset }) {
  const c = CATEGORY_COLORS[asset.category] ?? DEFAULT_COLOR;
  return (
    <Link
      href={`/asset/${asset.symbol}`}
      className="group relative overflow-hidden rounded-xl border border-white/[0.09] bg-panel p-4 transition-all hover:border-violet/40 hover:bg-panel2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet"
    >
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px transition-opacity group-hover:opacity-100"
        style={{ background: c.text, opacity: 0.3 }}
        aria-hidden="true"
      />
      <div className="mb-2 flex items-start justify-between gap-2">
        <div>
          <p className="font-mono text-sm font-bold text-text">{asset.symbol}</p>
          <p className="mt-0.5 text-xs text-muted line-clamp-1">{asset.name}</p>
        </div>
        <span
          className="shrink-0 rounded-md border px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-wider"
          style={{
            color: asset.asset_type === "stock" ? "#9B7BFF" : c.text,
            borderColor: asset.asset_type === "stock" ? "rgba(155,123,255,0.3)" : c.border,
          }}
        >
          {asset.asset_type}
        </span>
      </div>

      <div className="flex items-baseline justify-between gap-1">
        {asset.last_price != null ? (
          <p className="font-mono text-base font-bold text-text">
            ${formatPrice(asset.last_price)}
          </p>
        ) : (
          <p className="font-mono text-sm text-muted/50">—</p>
        )}
        {asset.change_24h_pct != null && (
          <Change24h pct={asset.change_24h_pct} />
        )}
      </div>

      <div className="mt-2 flex items-center justify-between gap-2">
        <CategoryBadge category={asset.category} />
        {asset.is_demo && (
          <span className="font-mono text-[9px] text-amber/70">demo</span>
        )}
      </div>
    </Link>
  );
}

type TypeFilter = "all" | "stock" | "crypto";

interface AssetGridProps {
  assets: ApiAsset[];
}

export default function AssetGrid({ assets }: AssetGridProps) {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [categoryFilter, setCategoryFilter] = useState("all");

  const categories = useMemo(() => {
    const all = new Set(assets.map((a) => a.category));
    return ["all", ...Array.from(all).sort()];
  }, [assets]);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return assets.filter((a) => {
      if (typeFilter !== "all" && a.asset_type !== typeFilter) return false;
      if (categoryFilter !== "all" && a.category !== categoryFilter) return false;
      if (q && !a.symbol.toLowerCase().includes(q) && !a.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [assets, query, typeFilter, categoryFilter]);

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <svg
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <input
            type="search"
            placeholder="Search by name or symbol…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-xl border border-white/[0.09] bg-panel py-2.5 pl-9 pr-4 font-mono text-sm text-text placeholder:text-muted/50 focus:border-violet/50 focus:outline-none"
          />
        </div>

        <div className="flex gap-2">
          {(["all", "stock", "crypto"] as TypeFilter[]).map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`rounded-lg border px-3 py-2 font-mono text-xs capitalize transition-colors ${
                typeFilter === t
                  ? "border-violet/50 bg-violet/10 text-violet-light"
                  : "border-white/[0.09] text-muted hover:border-white/20"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategoryFilter(cat)}
            className={`rounded-full border px-2.5 py-1 font-mono text-[10px] transition-colors ${
              categoryFilter === cat
                ? "border-violet/50 bg-violet/10 text-violet-light"
                : "border-white/[0.09] text-muted hover:border-white/20"
            }`}
          >
            {cat === "all" ? "All categories" : cat}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="flex min-h-48 flex-col items-center justify-center gap-3 rounded-xl border border-white/[0.05] py-16 text-center">
          <p className="font-mono text-sm text-muted">No assets match your search.</p>
          <button
            onClick={() => { setQuery(""); setTypeFilter("all"); setCategoryFilter("all"); }}
            className="font-mono text-xs text-violet-light underline-offset-4 hover:underline"
          >
            Clear filters
          </button>
        </div>
      ) : (
        <>
          <p className="mb-4 font-mono text-xs text-muted">
            {filtered.length} asset{filtered.length !== 1 ? "s" : ""}
          </p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {filtered.map((asset) => (
              <AssetCard key={asset.symbol} asset={asset} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
