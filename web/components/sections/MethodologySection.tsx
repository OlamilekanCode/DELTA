import Link from "next/link";
import SectionReveal from "@/components/shared/SectionReveal";

const disclaimers = [
  {
    title: "Historical relationship, not prediction",
    body: "Exposure Scores measure how two assets have moved similarly in the past 90 days. Past correlation does not guarantee future correlation or equivalent performance.",
    icon: (
      <svg className="size-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
      </svg>
    ),
  },
  {
    title: "Correlation can change",
    body: "Market regime shifts, macroeconomic events, and sector rotations can rapidly alter correlations. DELTA recalculates scores after each market close.",
    icon: (
      <svg className="size-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
      </svg>
    ),
  },
  {
    title: "Not investment advice",
    body: "DELTA is an analytical tool. Nothing on this platform constitutes financial advice, a recommendation to buy or sell any asset, or a forecast of returns.",
    icon: (
      <svg className="size-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
      </svg>
    ),
  },
];

export default function MethodologySection() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-24 lg:px-8" aria-labelledby="methodology-heading">
      <SectionReveal>
        <p className="mb-3 font-mono text-xs font-medium uppercase tracking-[0.2em] text-muted">
          Methodology
        </p>
        <h2 id="methodology-heading" className="font-heading text-3xl font-bold text-text sm:text-4xl">
          Transparent by design.
        </h2>
      </SectionReveal>

      <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-3">
        {disclaimers.map((d, i) => (
          <SectionReveal key={d.title} delay={i * 0.1}>
            <article className="flex flex-col rounded-2xl border border-white/[0.09] bg-panel p-6 h-full">
              <div className="mb-4 flex size-10 items-center justify-center rounded-xl bg-amber/10 text-amber">
                {d.icon}
              </div>
              <h3 className="mb-2 font-heading text-base font-semibold text-text">{d.title}</h3>
              <p className="text-sm leading-relaxed text-muted">{d.body}</p>
            </article>
          </SectionReveal>
        ))}
      </div>

      <SectionReveal delay={0.2}>
        <div className="mt-8 text-center">
          <Link
            href="/methodology"
            className="inline-flex items-center gap-2 text-sm font-medium text-violet-light transition-colors hover:text-violet focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet"
          >
            Read the full methodology
            <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
            </svg>
          </Link>
        </div>
      </SectionReveal>
    </section>
  );
}
