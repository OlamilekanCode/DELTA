import type { Metadata } from "next";
import { fetchAssets } from "@/lib/api";
import type { ApiAsset } from "@/lib/types";
import AssetGrid from "@/components/explore/AssetGrid";

export const metadata: Metadata = {
  title: "Explore — Synthetic Exposure",
  description: "Search supported stocks and discover connected crypto assets by Exposure Score.",
};

export default async function ExplorePage() {
  let assets: ApiAsset[] = [];

  try {
    const data = await fetchAssets();
    assets = data.assets;
  } catch {
    // API unavailable — render empty grid with error state
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
      <div className="mb-8">
        <p className="mb-2 font-mono text-xs font-medium uppercase tracking-[0.25em] text-violet">
          Market Explorer
        </p>
        <h1 className="font-heading text-3xl font-bold text-text sm:text-4xl">
          Stocks &amp; Crypto
        </h1>
        <p className="mt-2 max-w-xl text-sm text-muted">
          {assets.length > 0
            ? `${assets.filter((a) => a.asset_type === "stock").length} stocks · ${assets.filter((a) => a.asset_type === "crypto").length} crypto assets · Click any asset for detailed charts and Exposure Scores.`
            : "Data unavailable — the API may be starting up. Try refreshing in a moment."}
        </p>

        {/* $SynthEx unlock callout */}
        <div
          className="mt-5 inline-flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-xl border px-4 py-2.5"
          style={{
            borderColor: "rgba(109,74,255,0.25)",
            background: "rgba(109,74,255,0.06)",
          }}
        >
          <div className="flex items-center gap-2">
            <span className="size-1.5 rounded-full bg-violet" aria-hidden="true" />
            <span className="font-mono text-xs font-bold text-violet-light">$SynthEx</span>
          </div>
          <span className="font-mono text-xs text-muted">
            Hold <span className="font-semibold text-violet-light">$SynthEx</span> to unlock an extended universe — far beyond the current {assets.filter((a) => a.asset_type === "stock").length} stocks &amp; {assets.filter((a) => a.asset_type === "crypto").length} crypto assets — plus advanced Exposure Scores and deeper graph levels.
          </span>
        </div>
      </div>

      {assets.length > 0 ? (
        <AssetGrid assets={assets} />
      ) : (
        <div className="flex min-h-64 items-center justify-center rounded-2xl border border-white/[0.05]">
          <p className="font-mono text-sm text-muted">Unable to load assets.</p>
        </div>
      )}
    </div>
  );
}
