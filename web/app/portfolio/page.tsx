import type { Metadata } from "next";
import PortfolioGate from "@/components/wallet/PortfolioGate";

export const metadata: Metadata = {
  title: "Portfolio — DELTA",
  description: "Read-only portfolio exposure analysis for $DELTA token holders.",
};

export default function PortfolioPage() {
  return <PortfolioGate />;
}
