interface FreshnessLabelProps {
  isDemo: boolean | null;
  provider?: string | null;
  /** ISO datetime string — shown as "updated X min ago" when provided */
  ts?: string | null;
  /** Calendar date string (YYYY-MM-DD) — shown verbatim when ts is absent */
  date?: string | null;
  className?: string;
}

function formatRelativeTime(isoString: string): string {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin} min ago`;
  const diffHr = Math.floor(diffMs / 3_600_000);
  if (diffHr < 24) return `${diffHr} hr ago`;
  return new Date(isoString).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function FreshnessLabel({
  isDemo,
  provider,
  ts,
  date,
  className = "",
}: FreshnessLabelProps) {
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

  const timeText = ts
    ? `updated ${formatRelativeTime(ts)}`
    : date ?? null;

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border border-green/30 bg-green/10 px-2 py-0.5 font-mono text-[10px] font-medium text-green ${className}`}
    >
      <span className="size-1.5 animate-pulse rounded-full bg-green" aria-hidden="true" />
      {label}
      {timeText && <span className="opacity-60"> · {timeText}</span>}
    </span>
  );
}
