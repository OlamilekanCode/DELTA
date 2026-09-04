import type { Metadata } from "next";
import ComingSoonShell from "@/components/shared/ComingSoonShell";

interface Props {
  params: Promise<{ symbol: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { symbol } = await params;
  return {
    title: `${symbol} — DELTA`,
    description: `Detailed charts, Exposure Scores, and methodology for ${symbol}.`,
  };
}

const icon = (
  <svg className="size-9" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
  </svg>
);

export default async function AssetPage({ params }: Props) {
  const { symbol } = await params;
  return (
    <ComingSoonShell
      title={`${symbol} — Asset Detail`}
      description={`Detailed price chart, Exposure Scores, and methodology for ${symbol} is on the way. Full asset pages with real market data are coming soon.`}
      icon={icon}
      backHref="/"
      backLabel="Back to home"
    />
  );
}
