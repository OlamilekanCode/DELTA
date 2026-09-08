"use client";

import { useReducedMotion } from "framer-motion";
import { useMarketStatus } from "@/hooks/useMarketStatus";

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function MarketStatusBadge({ className = "" }: { className?: string }) {
  const status = useMarketStatus();
  const reduced = useReducedMotion();

  if (!status) return null;

  const label = status.is_open ? "Market open" : "US market closed";
  const detail = status.is_open ? null : `Last calc ${formatTime(status.last_close)}`;

  // Literal class strings per branch — Tailwind can't see runtime-interpolated
  // class names (`border-${color}/40`), so they must be spelled out in full.
  const colorClasses = status.is_open
    ? "border-green/40 bg-green/10 text-green"
    : "border-blue/40 bg-blue/10 text-blue";
  const dotClasses = status.is_open ? "bg-green" : "bg-blue";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-widest ${colorClasses} ${className}`}
      aria-label={`${label}${detail ? ` — ${detail}` : ""}`}
      title={detail ?? undefined}
    >
      <span
        className={`size-1.5 rounded-full ${dotClasses} ${reduced ? "" : "animate-pulse"}`}
        aria-hidden="true"
      />
      {label}
    </span>
  );
}
