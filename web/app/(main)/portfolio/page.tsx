import type { Metadata } from "next";
import PortfolioExposure from "@/components/portfolio/PortfolioExposure";
import { fetchAssetsAuthed } from "@/lib/server-api";
import type { ApiAsset } from "@/lib/types";

export const metadata: Metadata = {
  title: "Portfolio — Synthetic Exposure",
  description: "Read-only portfolio exposure analysis for $SynthEx token holders.",
};

export default async function PortfolioPage() {
  let stocks: ApiAsset[] = [];
  try {
    // Respects the caller's own tier — an authenticated holder session sees
    // the full 20-stock catalogue, a guest/non-holder session sees only the
    // free 8. Used to populate the stock selector, not for access control.
    const data = await fetchAssetsAuthed("stock");
    stocks = data.assets;
  } catch {
    // API unavailable — the client falls back to the single ranked view.
  }

  return <PortfolioExposure stocks={stocks} />;
}
