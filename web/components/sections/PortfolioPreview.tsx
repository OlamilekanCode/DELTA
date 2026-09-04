import Link from "next/link";
import DemoDataBadge from "@/components/shared/DemoDataBadge";
import SectionReveal from "@/components/shared/SectionReveal";

const categories = [
  { label: "AI / Technology",   pct: 37, color: "bg-green" },
  { label: "DeFi",              pct: 24, color: "bg-blue" },
  { label: "BTC Ecosystem",     pct: 22, color: "bg-amber" },
  { label: "Other / Unpriced",  pct: 17, color: "bg-panel2" },
];

export default function PortfolioPreview() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-24 lg:px-8" aria-labelledby="portfolio-heading">
      <div className="overflow-hidden rounded-2xl border border-white/[0.09] bg-panel">
        <div className="grid grid-cols-1 lg:grid-cols-2">
          {/* Copy */}
          <div className="p-8 lg:p-12">
            <SectionReveal>
              <p className="mb-3 font-mono text-xs font-medium uppercase tracking-[0.2em] text-violet">
                Portfolio Exposure
              </p>
              <h2 id="portfolio-heading" className="font-heading text-3xl font-bold text-text sm:text-4xl">
                Understand your crypto exposure.
              </h2>
              <p className="mt-4 text-base leading-relaxed text-muted">
                Connect a wallet and DELTA reads your public on-chain holdings — read-only, no transaction required. It calculates your portfolio&apos;s category exposure and weighted stock correlation score.
              </p>

              <div className="mt-6 rounded-xl border border-green/20 bg-green/5 p-4 font-mono text-sm">
                <p className="text-green">
                  Your supported holdings show{" "}
                  <span className="font-bold">37% AI/technology</span> category exposure and a weighted NVDA Exposure Score of{" "}
                  <span className="font-bold">0.42</span>.
                </p>
                <DemoDataBadge className="mt-2" />
              </div>

              <Link
                href="/portfolio"
                className="mt-8 inline-flex items-center gap-2 rounded-lg bg-violet px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet/25 transition-all hover:bg-violet-light focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet active:scale-95"
              >
                Connect wallet to analyze
              </Link>
            </SectionReveal>
          </div>

          {/* Visual */}
          <div className="flex flex-col justify-center border-t border-white/[0.09] p-8 lg:border-l lg:border-t-0 lg:p-12">
            <SectionReveal delay={0.1}>
              <p className="mb-4 font-mono text-xs font-medium uppercase tracking-widest text-muted">
                Portfolio breakdown
              </p>
              {/* Bar chart */}
              <div className="space-y-4">
                {categories.map((cat) => (
                  <div key={cat.label}>
                    <div className="mb-1.5 flex items-center justify-between font-mono text-xs">
                      <span className="text-muted">{cat.label}</span>
                      <span className="text-text">{cat.pct}%</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-panel2">
                      <div
                        className={`h-full rounded-full ${cat.color} transition-all`}
                        style={{ width: `${cat.pct}%` }}
                        role="presentation"
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6 flex items-center gap-2">
                <div className="size-2 rounded-full bg-muted" />
                <p className="font-mono text-xs text-muted">
                  Weighted NVDA Exposure Score: <span className="text-violet font-bold">0.42</span>
                </p>
              </div>
              <DemoDataBadge className="mt-3" />
            </SectionReveal>
          </div>
        </div>
      </div>
    </section>
  );
}
