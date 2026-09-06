import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchAsset, fetchAssetHistory, fetchExposures } from "@/lib/api";
import type { ApiAsset, ApiAssetHistoryOut, ApiExposuresResult } from "@/lib/types";
import FreshnessLabel from "@/components/shared/FreshnessLabel";
import StockExposureList from "@/components/asset/StockExposureList";
import AssetHistoryChartClient from "@/components/asset/AssetHistoryChartClient";

const CATEGORY_COLORS: Record<string, string> = {
  "Layer 1": "#F4C95D", "Layer 2": "#3D7BFF", "DeFi": "#9B7BFF",
  "Oracle/Data": "#38BDF8", "AI/Compute": "#71F79F", "Storage": "#FB923C",
  "Memecoin": "#F472B6", "Technology": "#9B7BFF", "Finance": "#2DD4BF",
};

interface Props {
  params: Promise<{ symbol: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { symbol } = await params;
  return {
    title: `${symbol.toUpperCase()} — DELTA`,
    description: `Price history, Exposure Scores and methodology for ${symbol.toUpperCase()}.`,
  };
}

function formatLargeNumber(n: number): string {
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9)  return `$${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6)  return `$${(n / 1e6).toFixed(2)}M`;
  return `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

function QuoteStats({ asset }: { asset: ApiAsset }) {
  if (asset.asset_type !== "crypto") return null;
  const hasQuote = asset.change_24h_pct != null || asset.market_cap_usd != null || asset.volume_24h_usd != null;
  if (!hasQuote) return null;

  return (
    <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
      {asset.change_24h_pct != null && (
        <div className="rounded-xl border border-white/[0.07] bg-panel p-3">
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted">24h change</p>
          <p className={`mt-1 font-mono text-lg font-bold ${asset.change_24h_pct >= 0 ? "text-green" : "text-red-400"}`}>
            {asset.change_24h_pct >= 0 ? "+" : ""}{asset.change_24h_pct.toFixed(2)}%
          </p>
        </div>
      )}
      {asset.market_cap_usd != null && (
        <div className="rounded-xl border border-white/[0.07] bg-panel p-3">
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Market cap</p>
          <p className="mt-1 font-mono text-lg font-bold text-text">{formatLargeNumber(asset.market_cap_usd)}</p>
        </div>
      )}
      {asset.volume_24h_usd != null && (
        <div className="rounded-xl border border-white/[0.07] bg-panel p-3">
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted">24h volume</p>
          <p className="mt-1 font-mono text-lg font-bold text-text">{formatLargeNumber(asset.volume_24h_usd)}</p>
        </div>
      )}
    </div>
  );
}

export default async function AssetPage({ params }: Props) {
  const { symbol } = await params;
  const sym = symbol.toUpperCase();

  let asset: ApiAsset | null = null;
  let history: ApiAssetHistoryOut | null = null;
  let exposures: ApiExposuresResult | null = null;

  try {
    [asset, history] = await Promise.all([fetchAsset(sym), fetchAssetHistory(sym)]);
  } catch {
    return notFound();
  }

  if (!asset) return notFound();

  if (asset.asset_type === "stock") {
    try {
      exposures = await fetchExposures(sym);
    } catch {
      // scores not yet available
    }
  }

  const chartColor = CATEGORY_COLORS[asset.category] ?? "#9B7BFF";

  return (
    <div className="min-h-screen pb-16">
      {/* Header */}
      <div
        className="border-b border-white/[0.07]"
        style={{ background: "linear-gradient(180deg, #060414 0%, #030508 100%)" }}
      >
        <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
          <Link
            href="/explore"
            className="mb-6 inline-flex items-center gap-1.5 font-mono text-xs text-muted transition-colors hover:text-text"
          >
            <svg className="size-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            Explore
          </Link>

          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span
                  className="rounded-md border px-2 py-0.5 font-mono text-xs font-semibold uppercase tracking-wider"
                  style={{ color: chartColor, borderColor: `${chartColor}40` }}
                >
                  {asset.asset_type}
                </span>
                <span className="font-mono text-xs text-muted">{asset.category}</span>
              </div>
              <h1 className="font-heading text-4xl font-bold text-text sm:text-5xl">{asset.symbol}</h1>
              <p className="mt-1 text-base text-muted">{asset.name}</p>
            </div>

            <div className="text-right">
              {asset.last_price != null && (
                <p className="font-mono text-3xl font-bold text-text">
                  ${asset.last_price < 0.01
                    ? asset.last_price.toFixed(6)
                    : asset.last_price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              )}
              {asset.last_price_date && (
                <p className="mt-1 font-mono text-xs text-muted">
                  {asset.asset_type === "stock" ? "Last close" : "Last recorded"} · {asset.last_price_date}
                </p>
              )}
              <div className="mt-2 flex justify-end">
                <FreshnessLabel
                  isDemo={asset.is_demo ?? null}
                  provider={asset.quote_provider ?? (asset.asset_type === "stock" ? "marketstack" : "coingecko")}
                  ts={asset.asset_type === "crypto" ? (asset.quote_ts ?? null) : null}
                  date={asset.last_price_date}
                />
              </div>
            </div>
          </div>

          {/* Quote stats row for crypto */}
          <QuoteStats asset={asset} />
        </div>
      </div>

      {/* Price history chart */}
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <h2 className="mb-4 font-heading text-xl font-bold text-text">Price History</h2>
        <div className="overflow-hidden rounded-2xl border border-white/[0.09] bg-panel p-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p className="font-mono text-xs text-muted">90-day daily close</p>
            {history && (
              <FreshnessLabel
                isDemo={history.is_demo ?? null}
                provider={history.provider}
              />
            )}
          </div>
          <div className="h-56 sm:h-72">
            {history && history.prices.length > 0 ? (
              <AssetHistoryChartClient prices={history.prices} color={chartColor} />
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="font-mono text-sm text-muted">No price history available.</p>
              </div>
            )}
          </div>
        </div>

        {asset.asset_type === "stock" && (
          <div className="mt-4 flex gap-3">
            <Link
              href={`/graph/${sym}`}
              className="inline-flex items-center gap-2 rounded-lg border border-violet/30 bg-violet/10 px-4 py-2.5 font-mono text-sm text-violet-light transition-colors hover:border-violet/50 hover:bg-violet/20"
            >
              Exposure Graph
              <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
            </Link>
            <Link
              href="/methodology"
              className="inline-flex items-center gap-2 rounded-lg border border-white/[0.09] px-4 py-2.5 font-mono text-sm text-muted transition-colors hover:border-white/20 hover:text-text"
            >
              Methodology
            </Link>
          </div>
        )}
      </div>

      {exposures && <StockExposureList exposures={exposures} stockSymbol={sym} />}
    </div>
  );
}
