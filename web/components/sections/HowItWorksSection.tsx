import SectionReveal from "@/components/shared/SectionReveal";

const steps = [
  {
    n: "01",
    title: "Search a stock",
    body: "Enter any supported stock ticker — NVDA, TSLA, COIN, MSTR — to see its historical market profile.",
    icon: (
      <svg className="size-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
    ),
  },
  {
    n: "02",
    title: "Compare historical movement",
    body: "DELTA calculates 90-day Pearson correlation between daily log returns, then produces a 0–1 Exposure Score.",
    icon: (
      <svg className="size-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
      </svg>
    ),
  },
  {
    n: "03",
    title: "Explore the Exposure Graph",
    body: "An interactive node graph shows every connected crypto asset, with score strength reflected in edge thickness and distance.",
    icon: (
      <svg className="size-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z" />
      </svg>
    ),
  },
];

export default function HowItWorksSection() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-24 lg:px-8" aria-labelledby="how-heading">
      <SectionReveal>
        <p className="mb-3 font-mono text-xs font-medium uppercase tracking-[0.2em] text-violet">
          How it works
        </p>
        <h2 id="how-heading" className="font-heading text-3xl font-bold text-text sm:text-4xl">
          From ticker to insights in seconds.
        </h2>
      </SectionReveal>

      <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-3">
        {steps.map((step, i) => (
          <SectionReveal key={step.n} delay={i * 0.1}>
            <article className="flex flex-col rounded-2xl border border-white/[0.09] bg-panel p-6 h-full">
              <div className="mb-4 flex size-12 items-center justify-center rounded-xl bg-violet/10 text-violet">
                {step.icon}
              </div>
              <p className="mb-1 font-mono text-xs text-muted">{step.n}</p>
              <h3 className="mb-2 font-heading text-lg font-semibold text-text">{step.title}</h3>
              <p className="text-sm leading-relaxed text-muted">{step.body}</p>
            </article>
          </SectionReveal>
        ))}
      </div>
    </section>
  );
}
