import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Methodology — Synthetic Exposure",
  description: "How Synthetic Exposure calculates Exposure Scores using 90-day Pearson correlation of daily log returns.",
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-12">
      <h2 className="mb-4 font-heading text-xl font-semibold text-text">{title}</h2>
      <div className="space-y-3 text-base leading-relaxed text-muted">{children}</div>
    </section>
  );
}

function Code({ children }: { children: React.ReactNode }) {
  return (
    <code className="rounded bg-panel2 px-2 py-0.5 font-mono text-sm text-violet-light">
      {children}
    </code>
  );
}

export default function MethodologyPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-28 lg:px-8">
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb" className="mb-8">
        <Link href="/" className="font-mono text-xs text-muted transition-colors hover:text-text">
          ← Back to home
        </Link>
      </nav>

      <header className="mb-12">
        <p className="mb-3 font-mono text-xs font-medium uppercase tracking-[0.2em] text-violet">
          Methodology
        </p>
        <h1 className="font-heading text-4xl font-bold text-text sm:text-5xl">
          How Synthetic Exposure calculates Exposure Scores
        </h1>
        <p className="mt-4 text-lg text-muted">
          Model version: <span className="font-mono text-violet-light">pearson_v1</span>
        </p>
      </header>

      <Section title="What is an Exposure Score?">
        <p>
          An Exposure Score is the signed Pearson correlation coefficient between a crypto asset
          and a stock over the past 90 days. It ranges from{" "}
          <strong className="text-text">−1.00</strong> (perfect inverse relationship) through{" "}
          <strong className="text-text">0.00</strong> (no linear relationship) to{" "}
          <strong className="text-text">+1.00</strong> (perfect positive relationship).
        </p>
        <p>
          A score of <strong className="text-text">+0.78</strong> means the two assets have had a
          strong positive price-movement relationship over the window. A score of{" "}
          <strong className="text-text">−0.62</strong> means an inverse relationship — when one
          rose the other tended to fall. A score near <strong className="text-text">0.00</strong>{" "}
          means no consistent linear relationship was detected.
        </p>
        <p>
          <strong className="text-text">This is not a forecast.</strong> An Exposure Score
          reflects past price-movement similarity, not guaranteed future behaviour.
        </p>
      </Section>

      <Section title="Inputs">
        <ul className="ml-4 list-disc space-y-2">
          <li>Adjusted daily closing prices for the selected stock (Marketstack)</li>
          <li>Daily crypto prices sampled at a consistent UTC timestamp (CoinGecko)</li>
          <li>Default lookback: <strong className="text-text">90 calendar days</strong></li>
          <li>Only dates on which the stock has a valid close are used</li>
          <li>Minimum <strong className="text-text">45 aligned observations</strong> required to compute a score</li>
        </ul>
      </Section>

      <Section title="Calculation steps">
        <ol className="ml-4 list-decimal space-y-3">
          <li>Sort prices oldest → newest</li>
          <li>
            Convert each price series to daily log returns:
            <div className="my-3 rounded-lg border border-white/[0.09] bg-panel p-4 font-mono text-sm text-violet-light">
              return_t = ln(price_t / price_&#123;t-1&#125;)
            </div>
          </li>
          <li>Align stock and crypto returns by date (inner join)</li>
          <li>
            Calculate Pearson correlation <Code>r</Code> across aligned observations — the result
            is the Exposure Score, stored without any clamp or transform:
            <div className="my-3 rounded-lg border border-white/[0.09] bg-panel p-4 font-mono text-sm text-violet-light">
              exposure_score = r &nbsp; &nbsp;(range: −1.00 to +1.00)
            </div>
          </li>
        </ol>
      </Section>

      <Section title="Score display">
        <p>
          Scores are always displayed with an explicit sign: <strong className="text-text">+0.78</strong>,{" "}
          <strong className="text-text">−0.62</strong>, <strong className="text-text">0.00</strong>.
          They are never shown as percentages. A score does not represent ownership, guaranteed
          exposure, or an equivalent percentage of price movement.
        </p>
        <p>
          Edge thickness in the Exposure Graph reflects magnitude (<Code>|r|</Code>). Colour
          reflects direction: violet for positive relationships, amber for inverse relationships.
        </p>
        <div className="rounded-xl border border-white/[0.09] bg-panel p-5 font-mono text-sm">
          <p className="text-text">NVDA ↔ BTC Exposure Score: <span className="font-bold text-violet">+0.78</span></p>
          <p className="mt-1 text-muted">NVDA ↔ DOGE Exposure Score: <span className="font-bold" style={{ color: "#FB923C" }}>−0.41</span></p>
          <p className="mt-1 text-muted">90-day historical relationship · 63 aligned observations</p>
          <p className="mt-1 text-muted">Model: pearson_v1</p>
        </div>
      </Section>

      <Section title="Data sources">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.09] text-left font-mono text-xs uppercase tracking-widest text-muted">
                <th className="pb-3 pr-6">Provider</th>
                <th className="pb-3 pr-6">Data</th>
                <th className="pb-3">Attribution</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.06]">
              <tr>
                <td className="py-3 pr-6 text-text">Marketstack</td>
                <td className="py-3 pr-6 text-muted">Stock daily OHLCV</td>
                <td className="py-3 text-muted">Per provider terms</td>
              </tr>
              <tr>
                <td className="py-3 pr-6 text-text">CoinGecko</td>
                <td className="py-3 pr-6 text-muted">Crypto daily prices</td>
                <td className="py-3 text-muted">Attribution required</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Update schedule">
        <p>
          Scores are recalculated after the relevant stock market closes and optionally every 6 hours.
          Scores are pre-computed and cached — they are <strong className="text-text">not</strong>{" "}
          recalculated during a page request.
        </p>
        <p>Data freshness is shown on every score card and graph node.</p>
      </Section>

      <Section title="Limitations">
        <ul className="ml-4 list-disc space-y-2">
          <li>The 90-day window may not capture long-term structural relationships</li>
          <li>Correlation can change rapidly with market regime shifts</li>
          <li>The crypto universe is limited to 30 curated assets</li>
          <li>Stock market holidays reduce observation counts</li>
          <li>
            Scores reflect price-movement similarity, not ownership, market-cap exposure, or
            guaranteed equivalent performance
          </li>
        </ul>
      </Section>

      <div className="rounded-2xl border border-danger/20 bg-danger/5 p-6">
        <h2 className="mb-3 font-heading text-lg font-semibold text-danger">Disclaimer</h2>
        <p className="text-sm leading-relaxed text-muted">
          Synthetic Exposure Exposure Scores are for informational and analytical purposes only. They do not
          constitute investment advice, a recommendation to buy or sell any asset, or a prediction of
          future performance. Historical correlation does not guarantee future correlation. Always
          conduct your own research before making any financial decision.
        </p>
      </div>

      {/* $SynthEx token callout */}
      <div className="mt-8 rounded-2xl border border-violet/20 bg-violet/[0.05] p-6">
        <div className="mb-2 flex items-center gap-2">
          <div className="size-1.5 rounded-full bg-violet" />
          <span className="font-mono text-xs font-bold uppercase tracking-widest text-violet-light">$SynthEx · Main Access Token</span>
        </div>
        <p className="text-sm leading-relaxed text-muted">
          Advanced analytics — including extended lookback windows, deeper graph levels, and wallet portfolio exposure — are gated behind the{" "}
          <strong className="text-violet-light">$SynthEx</strong> token. Hold $SynthEx to unlock premium features when they launch.
        </p>
      </div>
    </div>
  );
}
