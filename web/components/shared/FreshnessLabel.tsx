interface FreshnessLabelProps {
  isDemo: boolean | null;
  provider?: string;
  date?: string | null;
  className?: string;
}

export default function FreshnessLabel({ isDemo, provider, date, className = "" }: FreshnessLabelProps) {
  if (isDemo === null) {
    // Data origin unknown — render nothing rather than a misleading label
    return null;
  }

  if (isDemo) {
    return (
      <span
        className={`inline-flex items-center gap-1 rounded-full border border-amber/30 bg-amber/10 px-2 py-0.5 font-mono text-[10px] font-medium text-amber ${className}`}
      >
        <span className="size-1.5 rounded-full bg-amber" aria-hidden="true" />
        Demo data
      </span>
    );
  }

  const label =
    provider === "coingecko"
      ? "CoinGecko"
      : provider === "marketstack"
        ? "Marketstack"
        : provider ?? "Live";

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border border-green/30 bg-green/10 px-2 py-0.5 font-mono text-[10px] font-medium text-green ${className}`}
    >
      <span className="size-1.5 animate-pulse rounded-full bg-green" aria-hidden="true" />
      {label}
      {date && <span className="opacity-60"> · {date}</span>}
    </span>
  );
}
