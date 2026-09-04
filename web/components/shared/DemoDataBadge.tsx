export default function DemoDataBadge({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border border-amber/40 bg-amber/10 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-widest text-amber ${className}`}
      aria-label="Demo data — not live market values"
    >
      <span className="size-1.5 rounded-full bg-amber" aria-hidden="true" />
      Demo data
    </span>
  );
}
