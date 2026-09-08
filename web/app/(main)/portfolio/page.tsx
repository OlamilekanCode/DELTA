import type { Metadata } from "next";
import PortfolioExposure from "@/components/portfolio/PortfolioExposure";

export const metadata: Metadata = {
  title: "Portfolio — Synthetic Exposure",
  description: "Read-only portfolio exposure analysis for $SynthEx token holders.",
};

export default function PortfolioPage() {
  return <PortfolioExposure />;
}
