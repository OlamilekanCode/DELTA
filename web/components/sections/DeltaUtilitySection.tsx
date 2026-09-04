import SectionReveal from "@/components/shared/SectionReveal";

type FeatureStatus = "available" | "phase2" | "phase3";

const features: { label: string; status: FeatureStatus; note: string }[] = [
  { label: "Advanced Exposure Scores",    status: "available",  note: "Available with $DELTA" },
  { label: "Deeper Graph Levels",         status: "available",  note: "Available with $DELTA" },
  { label: "Portfolio Exposure",          status: "available",  note: "Available with $DELTA" },
  { label: "Real-Time Alerts",            status: "phase2",     note: "Coming soon" },
  { label: "Live Score Updates",          status: "phase2",     note: "Coming soon" },
  { label: "Live Price Feeds",            status: "phase2",     note: "Coming soon" },
  { label: "Live Graph Movement",         status: "phase2",     note: "Coming soon" },
  { label: "More Assets & Chains",        status: "phase2",     note: "Coming soon" },
  { label: "Automated Baskets",           status: "phase3",     note: "Coming in Phase 3" },
  { label: "Developer API",               status: "phase3",     note: "Coming in Phase 3" },
];

const statusStyles = {
  available: { dot: "bg-green",   text: "text-green",        badge: "border-green/30 bg-green/10 text-green" },
  phase2:    { dot: "bg-amber",   text: "text-amber",        badge: "border-amber/30 bg-amber/10 text-amber" },
  phase3:    { dot: "bg-muted",   text: "text-muted",        badge: "border-white/[0.09] bg-panel2 text-muted" },
} as const;

export default function DeltaUtilitySection() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-24 lg:px-8" aria-labelledby="delta-utility-heading">
      <SectionReveal>
        <p className="mb-3 font-mono text-xs font-medium uppercase tracking-[0.2em] text-violet">
          $DELTA utility token
        </p>
        <h2 id="delta-utility-heading" className="font-heading text-3xl font-bold text-text sm:text-4xl">
          Unlock deeper market insight.
        </h2>
        <p className="mt-4 max-w-lg text-base text-muted">
          Hold $DELTA to unlock advanced analytics. Free users see the public NVDA example; token holders get the full platform.
        </p>
      </SectionReveal>

      <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((f, i) => {
          const s = statusStyles[f.status];
          return (
            <SectionReveal key={f.label} delay={i * 0.05}>
              <div className="flex items-start gap-3 rounded-xl border border-white/[0.09] bg-panel p-4">
                <span className={`mt-0.5 size-2 shrink-0 rounded-full ${s.dot}`} aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-text">{f.label}</p>
                </div>
                <span className={`shrink-0 rounded-full border px-2 py-0.5 font-mono text-[10px] ${s.badge}`}>
                  {f.note}
                </span>
              </div>
            </SectionReveal>
          );
        })}
      </div>
    </section>
  );
}
