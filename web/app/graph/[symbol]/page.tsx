import type { Metadata } from "next";
import ComingSoonShell from "@/components/shared/ComingSoonShell";

interface Props {
  params: Promise<{ symbol: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { symbol } = await params;
  return {
    title: `${symbol} Exposure Graph — DELTA`,
    description: `Full interactive Exposure Graph for ${symbol} with zoom, pan, filters, and depth controls.`,
  };
}

const icon = (
  <svg className="size-9" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z" />
  </svg>
);

export default async function GraphPage({ params }: Props) {
  const { symbol } = await params;
  return (
    <ComingSoonShell
      title={`${symbol} — Exposure Graph`}
      description={`The full-page interactive Exposure Graph for ${symbol} — with search, zoom, pan, and depth controls — is on the way.`}
      icon={icon}
      backHref="/"
      backLabel="Back to home"
    />
  );
}
