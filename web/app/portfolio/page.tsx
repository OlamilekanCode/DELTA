import type { Metadata } from "next";
import ComingSoonShell from "@/components/shared/ComingSoonShell";

export const metadata: Metadata = {
  title: "Portfolio Exposure — DELTA",
  description: "Read-only portfolio exposure analysis for $DELTA token holders.",
};

const icon = (
  <svg className="size-9" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 12m18 0v5.25A2.25 2.25 0 0 1 18.75 19.5H5.25A2.25 2.25 0 0 1 3 17.25V12m18 0V6.75A2.25 2.25 0 0 0 18.75 4.5H5.25A2.25 2.25 0 0 0 3 6.75V12" />
  </svg>
);

export default function PortfolioPage() {
  return (
    <ComingSoonShell
      title="Portfolio Exposure"
      description="Connect your wallet and hold $DELTA to unlock read-only portfolio exposure analysis — category breakdown, weighted stock scores, and more. Full portfolio features are coming soon."
      icon={icon}
      backHref="/"
      backLabel="Back to home"
    />
  );
}
