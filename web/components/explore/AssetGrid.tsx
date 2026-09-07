"use client";

import Link from "next/link";
import { useMemo, useState, useEffect } from "react";
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

const PAGE_SIZE = 12;

function formatPrice(price: number): string {
  if (price < 0.0001) return price.toFixed(8);
  if (price < 0.01)   return price.toFixed(6);
  if (price < 1)      return price.toFixed(4);
  if (price < 100)    return price.toFixed(2);
  return price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatMarketCap(mc: number): string {
  if (mc >= 1e12) return `$${(mc / 1e12).toFixed(2)}T`;
  if (mc >= 1e9)  return `$${(mc / 1e9).toFixed(2)}B`;
  if (mc >= 1e6)  return `$${(mc / 1e6).toFixed(1)}M`;
  return `$${mc.toLocaleString()}`;
}

function CategoryBadge({ category }: { category: string }) {
  const c = CATEGORY_COLORS[category] ?? DEFAULT_COLOR;
  return (
    <span
      className="rounded-full px-2 py-0.5 font-mono text-[11px] font-medium"
      style={{ color: c.text, background: c.bg, border: `1px solid ${c.border}` }}
    >
      {category}
    </span>
  );
}

function Change24h({ pct }: { pct: number }) {
  const positive = pct >= 0;
  return (
    <span className={`font-mono text-xs font-semibold ${positive ? "text-green" : "text-red-400"}`}>
      {positive ? "+" : ""}{pct.toFixed(2)}%
    </span>
  );
}

function AssetCard({ asset }: { asset: ApiAsset }) {
  const c = CATEGORY_COLORS[asset.category] ?? DEFAULT_COLOR;
  return (
    <Link
      href={`/asset/${asset.symbol}`}
      className="group relative overflow-hidden rounded-xl border border-white/[0.09] bg-panel p-5 transition-all hover:border-violet/40 hover:bg-panel2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet"
    >
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px transition-opacity group-hover:opacity-100"
        style={{ background: c.text, opacity: 0.35 }}
        aria-hidden="true"
      />

      {/* Header row */}
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <p className="font-mono text-base font-bold text-text">{asset.symbol}</p>
          <p className="mt-0.5 text-sm text-muted line-clamp-1">{asset.name}</p>
        </div>
        <span
          className="shrink-0 rounded-md border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider"
          style={{
            color: asset.asset_type === "stock" ? "#9B7BFF" : c.text,
            borderColor: asset.asset_type === "stock" ? "rgba(155,123,255,0.3)" : c.border,
          }}
        >
          {asset.asset_type}
        </span>
      </div>

      {/* Price row */}
      <div className="flex items-baseline justify-between gap-2">
        {asset.last_price != null ? (
          <p className="font-mono text-lg font-bold text-text">
            ${formatPrice(asset.last_price)}
          </p>
        ) : (
          <p className="font-mono text-base text-muted">—</p>
        )}
        {asset.change_24h_pct != null && (
          <Change24h pct={asset.change_24h_pct} />
        )}
      </div>

      {/* Market cap (if available) */}
      {asset.market_cap_usd != null && (
        <p className="mt-1 font-mono text-xs text-muted">
          Mkt cap {formatMarketCap(asset.market_cap_usd)}
        </p>
      )}

      {/* Footer row */}
      <div className="mt-3 flex items-center justify-between gap-2">
        <CategoryBadge category={asset.category} />
        {asset.is_demo && (
          <span className="font-mono text-[9px] text-amber/70">demo</span>
        )}
      </div>
    </Link>
  );
}

function Pagination({
  page,
  totalPages,
  onChange,
}: {
  page: number;
  totalPages: number;
  onChange: (p: number) => void;
}) {
  if (totalPages <= 1) return null;

  const pages: (number | "…")[] = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (page > 3) pages.push("…");
    for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) pages.push(i);
    if (page < totalPages - 2) pages.push("…");
    pages.push(totalPages);
  }

  const btnBase =
    "flex size-9 items-center justify-center rounded-lg border font-mono text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet";
  const active  = "border-violet/50 bg-violet/10 text-violet-light";
  const inactive = "border-white/[0.09] text-muted hover:border-white/20 hover:text-text";
  const disabled = "border-white/[0.05] text-muted/30 cursor-not-allowed";

  return (
    <div className="mt-10 flex items-center justify-center gap-1.5" role="navigation" aria-label="Pagination">
      <button
        onClick={() => onChange(page - 1)}
        disabled={page === 1}
        className={`${btnBase} ${page === 1 ? disabled : inactive}`}
        aria-label="Previous page"
      >
        <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
        </svg>
      </button>

      {pages.map((p, i) =>
        p === "…" ? (
          <span key={`ellipsis-${i}`} className="flex size-9 items-center justify-center font-mono text-sm text-muted">
            …
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onChange(p)}
            className={`${btnBase} ${p === page ? active : inactive}`}
            aria-label={`Page ${p}`}
            aria-current={p === page ? "page" : undefined}
          >
            {p}
          </button>
        )
      )}

      <button
        onClick={() => onChange(page + 1)}
        disabled={page === totalPages}
        className={`${btnBase} ${page === totalPages ? disabled : inactive}`}
        aria-label="Next page"
      >
        <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
        </svg>
      </button>
    </div>
  );
}

type TypeFilter = "all" | "stock" | "crypto";

interface AssetGridProps {
  assets: ApiAsset[];
}

function popularityScore(a: ApiAsset): number {
  if (a.market_cap_usd != null) return a.market_cap_usd;
  if (a.last_price != null) return a.last_price * 1e6;
  return 0;
}

export default function AssetGrid({ assets }: AssetGridProps) {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [page, setPage] = useState(1);

  useEffect(() => { setPage(1); }, [query, typeFilter, categoryFilter]);

  const categories = useMemo(() => {
    const all = new Set(assets.map((a) => a.category));
    return ["all", ...Array.from(all).sort()];
  }, [assets]);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return assets
      .filter((a) => {
        if (typeFilter !== "all" && a.asset_type !== typeFilter) return false;
        if (categoryFilter !== "all" && a.category !== categoryFilter) return false;
        if (q && !a.symbol.toLowerCase().includes(q) && !a.name.toLowerCase().includes(q)) return false;
        return true;
      })
      .sort((a, b) => popularityScore(b) - popularityScore(a));
  }, [assets, query, typeFilter, categoryFilter]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div>
      {/* Search + type filter row */}
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <svg
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <input
            type="search"
            placeholder="Search by name or symbol…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-xl border border-white/[0.09] bg-panel py-3 pl-9 pr-4 font-mono text-sm text-text placeholder:text-muted/60 focus:border-violet/50 focus:outline-none"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          {(["all", "stock", "crypto"] as TypeFilter[]).map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`rounded-lg border px-4 py-2.5 font-mono text-sm capitalize transition-colors ${
                typeFilter === t
                  ? "border-violet/50 bg-violet/10 text-violet-light"
                  : "border-white/[0.09] text-muted hover:border-white/20 hover:text-text"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Category pills */}
      <div className="mb-6 flex flex-wrap gap-2">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategoryFilter(cat)}
            className={`rounded-full border px-3.5 py-1.5 font-mono text-xs font-medium transition-colors ${
              categoryFilter === cat
                ? "border-violet/50 bg-violet/10 text-violet-light"
                : "border-white/[0.09] text-muted hover:border-white/20 hover:text-text"
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
          <p className="mb-5 font-mono text-xs text-muted">
            {filtered.length} asset{filtered.length !== 1 ? "s" : ""}
            {totalPages > 1 && ` · page ${page} of ${totalPages}`}
          </p>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {paginated.map((asset) => (
              <AssetCard key={asset.symbol} asset={asset} />
            ))}
          </div>

          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        </>
      )}
    </div>
  );
}
