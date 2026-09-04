import dynamic from "next/dynamic";
import DemoDataBadge from "@/components/shared/DemoDataBadge";
import SectionReveal from "@/components/shared/SectionReveal";
import { topExposureScores } from "@/lib/fixtures/exposure-scores";

const NVDAChart = dynamic(() => import("./NVDAChart"), {
  ssr: false,
  loading: () => (
    <div className="h-64 w-full animate-pulse rounded-xl bg-panel2" aria-label="Loading chart" />
  ),
});

const CATEGORY_COLORS: Record<string, string> = {
  "BTC Ecosystem": "text-amber",
  "DeFi":          "text-blue",
  "AI":            "text-green",
};

function ScoreBar({ value }: { value: number }) {
  return (
    <div className="h-1 w-full overflow-hidden rounded-full bg-panel2" role="presentation">
      <div
        className="h-full rounded-full bg-violet transition-all"
        style={{ width: `${value * 100}%` }}
      />
    </div>
  );
}

export default function NVDAExampleSection() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-24 lg:px-8" aria-labelledby="nvda-heading">
      <SectionReveal>
        <div className="mb-2 flex items-center gap-3">
          <p className="font-mono text-xs font-medium uppercase tracking-[0.2em] text-violet">
            Live example
          </p>
          <DemoDataBadge />
        </div>
        <h2 id="nvda-heading" className="font-heading text-3xl font-bold text-text sm:text-4xl">
          NVDA — Exposure Scores
        </h2>
        <p className="mt-3 max-w-lg text-base text-muted">
          90-day historical relationship · 63 aligned observations
        </p>
      </SectionReveal>

      <div className="mt-10 grid grid-cols-1 gap-8 lg:grid-cols-5">
        {/* Chart — 3/5 */}
        <SectionReveal className="lg:col-span-3" delay={0.05}>
          <div className="overflow-hidden rounded-2xl border border-white/[0.09] bg-panel p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <p className="font-mono text-xs text-muted">Normalized performance (base = 100)</p>
              <div className="flex items-center gap-4 font-mono text-xs">
                <span className="flex items-center gap-1.5"><span className="inline-block size-2 rounded-full bg-violet" />NVDA</span>
                <span className="flex items-center gap-1.5"><span className="inline-block size-2 rounded-full bg-amber" />BTC</span>
                <span className="flex items-center gap-1.5"><span className="inline-block size-2 rounded-full bg-blue" />ETH</span>
              </div>
            </div>
            <div className="h-64 w-full">
              <NVDAChart />
            </div>
          </div>
        </SectionReveal>

        {/* Score cards — 2/5 */}
        <SectionReveal className="flex flex-col gap-3 lg:col-span-2" delay={0.1}>
          <p className="font-mono text-xs font-medium uppercase tracking-widest text-muted">
            Top Exposure Scores
          </p>
          {topExposureScores.map((s) => (
            <article
              key={s.symbol}
              className="rounded-xl border border-white/[0.09] bg-panel p-4"
            >
              <div className="mb-2 flex items-center justify-between">
                <div>
                  <span className="font-mono text-sm font-medium text-text">{s.symbol}</span>
                  <span className={`ml-2 font-mono text-xs ${CATEGORY_COLORS[s.category] ?? "text-muted"}`}>
                    {s.category}
                  </span>
                </div>
                <span className="font-mono text-sm font-bold text-violet">{s.score.toFixed(2)}</span>
              </div>
              <ScoreBar value={s.score} />
              <p className="mt-1.5 font-mono text-[10px] text-muted">
                {s.observations} observations
              </p>
            </article>
          ))}
        </SectionReveal>
      </div>
    </section>
  );
}
