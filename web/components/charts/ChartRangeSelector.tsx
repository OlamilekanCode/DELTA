"use client";

export type ChartRange = "4H" | "1D" | "1W" | "1M" | "3M" | "1Y";

const RANGES: ChartRange[] = ["4H", "1D", "1W", "1M", "3M", "1Y"];

interface Props {
  value: ChartRange;
  onChange: (range: ChartRange) => void;
  className?: string;
}

export default function ChartRangeSelector({ value, onChange, className = "" }: Props) {
  return (
    <div className={`inline-flex items-center gap-1 rounded-lg border border-white/[0.09] bg-panel2 p-1 ${className}`}>
      {RANGES.map((r) => {
        const active = value === r;
        return (
          <button
            key={r}
            type="button"
            onClick={() => onChange(r)}
            aria-pressed={active}
            className={`rounded-md px-2.5 py-1 font-mono text-xs font-semibold transition-colors ${
              active
                ? "bg-violet text-white"
                : "text-muted hover:bg-white/[0.06] hover:text-text"
            }`}
          >
            {r}
          </button>
        );
      })}
    </div>
  );
}
