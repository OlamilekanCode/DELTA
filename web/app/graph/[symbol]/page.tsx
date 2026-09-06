import type { Metadata } from "next";
import Link from "next/link";
import { fetchGraph } from "@/lib/api";
import type { ApiGraphResult } from "@/lib/types";
import FreshnessLabel from "@/components/shared/FreshnessLabel";
import ExposureGraphCanvasClient from "@/components/graph/ExposureGraphCanvasClient";

interface Props {
  params: Promise<{ symbol: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { symbol } = await params;
  return {
    title: `${symbol.toUpperCase()} Exposure Graph — DELTA`,
    description: `Interactive crypto Exposure Graph for ${symbol.toUpperCase()} — zoom, pan, score filtering.`,
  };
}

export default async function GraphPage({ params }: Props) {
  const { symbol } = await params;
  const sym = symbol.toUpperCase();

  let graphData: ApiGraphResult | null = null;

  try {
    graphData = await fetchGraph(sym);
  } catch {
    // API unavailable — render empty graph
  }

  return (
    <div className="flex h-[calc(100vh-64px)] flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 border-b border-white/[0.07] px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <Link
            href={`/asset/${sym}`}
            className="inline-flex items-center gap-1.5 font-mono text-xs text-muted transition-colors hover:text-text"
          >
            <svg className="size-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            {sym}
          </Link>
          <span className="text-muted/30">·</span>
          <h1 className="font-mono text-sm font-semibold text-text">Exposure Graph</h1>
        </div>

        <div className="flex items-center gap-3">
          {graphData && (
            <FreshnessLabel isDemo={graphData.demo} />
          )}
          <span className="font-mono text-xs text-muted">
            {graphData ? `${graphData.edges.length} connections` : ""}
          </span>
          <Link
            href="/methodology"
            className="font-mono text-xs text-muted/60 transition-colors hover:text-muted"
          >
            Methodology
          </Link>
        </div>
      </div>

      {/* Graph canvas */}
      <div className="relative flex-1 overflow-hidden bg-bg">
        {graphData && graphData.nodes.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <p className="font-mono text-sm text-muted">No Exposure Scores computed yet.</p>
              <p className="mt-2 font-mono text-xs text-muted/60">
                Run <code className="text-violet">recompute-scores</code> to populate.
              </p>
            </div>
          </div>
        ) : (
          <ExposureGraphCanvasClient graphData={graphData} />
        )}
      </div>
    </div>
  );
}
